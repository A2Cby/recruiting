
# Recruiting API

API for matching candidates to job vacancies using NLP and machine learning.

## Database Structure

The system uses a PostgreSQL database with three main tables:
- `person_data`: Basic candidate profiles
- `education_data`: Education history 
- `position_data`: Work experience

## Quick Start
0. Install dependencies, env variables, and create a PostgreSQL database connection
1. See `usage_example.ipynb` for complete code examples
2. Connect to your PostgreSQL database
3. Format candidate data correctly
4. Submit candidates with a vacancy description
5. Retrieve and analyze match results

## Docker Setup
docker build -t recruiting-api:latest .
docker save recruiting-api:latest -o recruiting-api.tar
scp recruiting-api.tar g.burdin@93.127.132.57:~/recruiting

On the server:
docker load -i recruiting-api.tar
docker run -d --env-file .env -p 8910:8910 --restart unless-stopped --name recruiting-api --network recruiting-net recruiting-api


Pay attention to the ports!

