import logging
import os
from typing import List, Dict, Optional
import pandas as pd
import psycopg2
from psycopg2.extras import RealDictCursor
from fastapi import HTTPException
from sshtunnel import SSHTunnelForwarder

from schemas.candidate import CandidateData
import dotenv
dotenv.load_dotenv()
logger = logging.getLogger(__name__)

def get_db_connection():
    try:
        logger.info("Establishing database connection via SSH tunnel...")
        ssh_tunnel_params = {
            'ssh_address_or_host': os.getenv("SSH_HOST"),
            'ssh_port': int(os.getenv("SSH_PORT")),  # Ensure port is an integer
            'ssh_username': os.getenv("SSH_USER"),
            'remote_bind_address': (os.getenv("DB_HOST"), int(os.getenv("DB_PORT"))),  # Ensure port is an integer
            "ssh_password": os.getenv("SSH_PASSWORD"),
        }

        # Create SSH tunnel and store in global variable
        tunnel = SSHTunnelForwarder(**ssh_tunnel_params)
        tunnel.start()

        logger.info(f"SSH Tunnel established to {ssh_tunnel_params["ssh_address_or_host"]} on local port {tunnel.local_bind_port}")

        # Connect to database through the SSH tunnel
        conn = psycopg2.connect(
            dbname=os.getenv("DB_NAME"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
            host=tunnel.local_bind_host,
            port=tunnel.local_bind_port
        )

        logger.info("Database connection through SSH tunnel established successfully.")
        return conn, tunnel
            
    except Exception as e:
        logger.error(f"SSH tunnel or database connection failed: {e}")
        return None

def fetch_candidates_from_db(keywords: Optional[List[str]] = None, location: Optional[str] = None,):
    """Fetches and formats candidate data, optionally filtering by keywords in skills or summary."""
    base_query = """
WITH edu AS (
    SELECT
        username,
        COALESCE(
            string_agg(
                format(
                    'edu: id=%%s, start_date=%%s, end_date=%%s, fieldOfStudy=%%s, degree=%%s, grade=%%s, schoolName=%%s, description=%%s, activities=%%s, schoolId=%%s',
                    id, start_date, end_date, "fieldOfStudy", degree, grade, "schoolName", description, activities, "schoolId"
                ),
                ' | '
            ),
            ''
        ) AS edu_text
    FROM education_data
    GROUP BY username
),
pos AS (
    SELECT
        username,
        COALESCE(
            string_agg(
                format(
                    'pos: id=%%s, companyId=%%s, companyName=%%s, companyUsername=%%s, companyIndustry=%%s, companyStaffCountRange=%%s, title=%%s, location=%%s, description=%%s, employmentType=%%s, start_date=%%s, end_date=%%s',
                    id, "companyId", "companyName", "companyUsername", "companyIndustry", "companyStaffCountRange",
                    title, location, description, "employmentType", start_date, end_date
                ),
                ' | '
            ),
            ''
        ) AS pos_text
    FROM position_data
    GROUP BY username
)
SELECT
    p.id,
    p."fullName",
    p.summary,
    p.skills,
    p.location,
    p.country,
    p.city,
    p."profileURL",
    concat_ws(' | ', edu_text, pos_text) AS combined_text
FROM person_data p
LEFT JOIN edu ON p.username = edu.username
LEFT JOIN pos ON p.username = pos.username
"""


    # Dynamically build WHERE clause for keywords
    where_clauses = []
    params = []
    if keywords:
        logger.info(f"Filtering candidates by keywords: {keywords}")
        # Create ILIKE conditions for each keyword against multiple fields
        keyword_conditions = []
        for kw in keywords:
            # Format for ILIKE and add to params
            like_pattern = f"%{kw}%"
            params.append(like_pattern)
            params.append(like_pattern)
            # Add OR conditions for skills and summary (adjust fields as needed)
            keyword_conditions.append(f"(p.skills ILIKE %s OR p.summary ILIKE %s)")

        # Combine keyword conditions with OR
        if keyword_conditions:
            where_clauses.append(f"({' OR '.join(keyword_conditions)})")

    if location:
        logger.info(f"Filtering candidates by location: {location}")
        # Add location condition to WHERE clause
        where_clauses.append(f"(p.location ILIKE %s OR p.country ILIKE %s OR p.city ILIKE %s)")
        params.append(f"%{location}%")
        params.append(f"%{location}%")
        params.append(f"%{location}%")
    # Construct final query
    final_query = base_query
    if where_clauses:
        final_query += " WHERE " + " AND ".join(where_clauses) # Use AND if combining with other future clauses
    final_query += " LIMIT 800;"

    conn, ssh_tunnel = get_db_connection()
    if not conn:
         raise HTTPException(status_code=503, detail="Database connection unavailable.")

    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # Log the constructed query and parameters before execution
            logger.debug(f"Executing DB query: {final_query}")
            param_tuple = tuple(params) if params else None
            logger.debug(f"With parameters: {param_tuple}")

            # Execute with parameters safely converted to tuple or None
            cur.execute(final_query, param_tuple)

            results = cur.fetchall()
            df_raw = pd.DataFrame(results)
            if df_raw.empty:
                logger.info("No candidates found matching the criteria.")
                return []

            df_raw['text'] = df_raw.apply(lambda row: "\n".join([
                f"fullName: {row.get('fullName', '')}",
                f"summary: {row.get('summary', '')}",
                f"skills: {row.get('skills', '')}",
                f"location: {row.get('location', '')}",
                f"country: {row.get('country', '')}",
                f"city: {row.get('city', '')}",
                f"combined_text: {row.get('combined_text', '')}"
            ]), axis=1)

            # Keep id, text, profileURL, and fullName
            df_candidates = df_raw[['id', 'text', 'profileURL', 'fullName']].copy()
            # Convert NaN/NaT/None to appropriate values
            df_candidates['profileURL'] = df_candidates['profileURL'].fillna('')
            df_candidates['fullName'] = df_candidates['fullName'].fillna('N/A') # Add default for name
            df_candidates = df_candidates.fillna('') # Fill other potential NaNs in text/id

            # Pass profileURL and fullName when creating CandidateData
            candidate_list = [CandidateData(**record) for record in df_candidates.to_dict(orient='records')]
            logger.info(f"Successfully fetched and processed {len(candidate_list)} candidates.")
            return candidate_list

    except (Exception, psycopg2.Error) as e:
        logger.error(f"Error fetching or processing candidates: {e}")
        raise HTTPException(status_code=500, detail="Error fetching candidates from database.")
    finally:
        if conn:
            conn.close()
            logger.info("Database connection closed.")
        
        # Close SSH tunnel if it exists
        if ssh_tunnel:
            try:
                ssh_tunnel.stop()
                logger.info("SSH tunnel closed.")
            except Exception as e:
                logger.error(f"Error closing SSH tunnel: {e}")

def fetch_candidate_details(candidate_ids: List[int]) -> Dict[int, Dict[str, str]]:
    """Fetches fullName and profileURL for a given list of candidate IDs."""
    if not candidate_ids:
        return {}

    conn, ssh_tunnel = get_db_connection()
    if not conn:
        logger.error("Cannot fetch candidate details: Database connection unavailable.")
        return {}

    id_tuple = tuple(candidate_ids)
    # Fetch id, fullName, and profileURL
    query = 'SELECT id, "fullName", "profileURL" FROM person_data WHERE id = ANY(%s);'

    details = {}
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(query, (id_tuple,))
            results = cur.fetchall()
            for row in results:
                details[row['id']] = {
                    "fullName": row.get('fullName', 'N/A'), # Provide default
                    "profileURL": row.get('profileURL', '')  # Provide default
                }
            logger.info(f"Fetched details for {len(details)} candidates.")
    except (Exception, psycopg2.Error) as e:
        logger.error(f"Error fetching candidate details: {e}")
    finally:
        if conn:
            conn.close()
            logger.info("Database connection closed after fetching details.")
        
        # Close SSH tunnel if it exists
        if ssh_tunnel:
            try:
                ssh_tunnel.stop()
                logger.info("SSH tunnel closed after fetching details.")
            except Exception as e:
                logger.error(f"Error closing SSH tunnel: {e}")
    return details 