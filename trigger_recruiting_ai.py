import os
import asyncio # Added import for asyncio
import psycopg2
import psycopg2.extras
from sshtunnel import SSHTunnelForwarder
import httpx
import dotenv
dotenv.load_dotenv()


async def process_single_vacancy(client, conn, vacancy_row):
    """
    Processes a single vacancy: calls the API and updates the database.
    """
    vacancy_id = vacancy_row['id']
    vacancy_title = vacancy_row['title']
    vacancy_description = vacancy_row['description']
    vacancy_location = vacancy_row['location'] if vacancy_row['location']!="" else "everywhere"
    vacancy_skills = vacancy_row['skills']
    vacancy_experience = vacancy_row['experience']
    with conn.cursor() as cur_update:  # Use a new cursor for thread safety
        query_update = "UPDATE vacancies_vec SET need_to_be_processed = FALSE WHERE id = %s;"
        cur_update.execute(query_update, (vacancy_id,))
        conn.commit()
    # Construct vacancy_text as expected by VacancyMatchRequest
    vacancy_text = (f"Vacancy title: {vacancy_title}\n"
                    f"Vacancy Description: {vacancy_description}\n "
                    f"Location: {vacancy_location}\n "
                    f"Skillset: {vacancy_skills}"
                    f"With {vacancy_experience} years of experience\n ")

    # Prepare payload for the API
    payload = {
        "vacancy_id": vacancy_id,
        "vacancy_text": vacancy_text
    }

    api_url = f"http://93.127.132.57:8910/api/v1/matching/match_candidates_batch"
    print(f"Calling API for vacancy ID {vacancy_id}: {api_url}")

    try:
        response = await client.post(api_url, json=payload)
        if response.status_code == 202:
            print(f"API call successful for vacancy ID {vacancy_id}. Response: {response.json()}")
            # Update the vacancy as processed in the database
            return True, vacancy_id, None
        else:
            error_message = f"API call for vacancy ID {vacancy_id} failed with status {response.status_code}: {response.text}"
            print(error_message)
            return False, vacancy_id, error_message
    except httpx.RequestError as exc:
        error_message = f"An error occurred while requesting {exc.request.url!r} for vacancy ID {vacancy_id}: {exc}"
        print(error_message)
        return False, vacancy_id, error_message
    except Exception as api_exc:
        error_message = f"An unexpected error during API call for vacancy ID {vacancy_id}: {api_exc}"
        print(error_message)
        return False, vacancy_id, error_message

async def process_new_vacancies_and_call_api():
    """
    Connects to the database via an SSH tunnel, fetches new vacancies,
    calls the /match_candidates_batch API for each concurrently, and updates their status.
    """

    ssh_tunnel_params = {
        'ssh_address_or_host': os.getenv("SSH_HOST"),
        'ssh_port': int(os.getenv("SSH_PORT")), # Ensure port is an integer
        'ssh_username': os.getenv("SSH_USER"),
        'remote_bind_address': (os.getenv("DB_HOST"), int(os.getenv("DB_PORT"))), # Ensure port is an integer
        "ssh_password": os.getenv("SSH_PASSWORD"),
    }
    try:
        with SSHTunnelForwarder(**ssh_tunnel_params) as tunnel:
            print(f"SSH Tunnel established to {os.getenv("SSH_HOST")} on local port {tunnel.local_bind_port}")
            conn = psycopg2.connect(
                dbname=os.getenv("DB_NAME"),
                user=os.getenv("DB_USER"),
                password=os.getenv("DB_PASSWORD"),
                host=tunnel.local_bind_host,
                port=tunnel.local_bind_port
            )
            # conn.autocommit = False
            print("Database connection successful via SSH tunnel.")

            async with httpx.AsyncClient(timeout=httpx.Timeout(60.0)) as client:
                with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                    cur.execute("""
                                SELECT id, title, description, location, skills, places, kinds, experience
                                FROM vacancies_vec
                                WHERE need_to_be_processed = TRUE LIMIT 1;
                                """)
                    vacancy = cur.fetchone()

                    if not vacancy:
                        print("No new vacancy to process.")
                        return

                    # process that single vacancy
                    success, vid, err = await process_single_vacancy(client, conn, vacancy)
                    if success:
                        print(f"Vacancy {vid} processed successfully.")
                    else:
                        print(f"Vacancy {vid} failed: {err}")

            conn.close()
            print("DB connection closed.")

    except Exception as e:
        print(f"Error: {e}")



if __name__ == "__main__":
    import asyncio
    asyncio.run(process_new_vacancies_and_call_api())
