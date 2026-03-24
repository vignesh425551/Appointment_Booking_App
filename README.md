# Healthcare Appointment Streamlit App

This project now includes a Streamlit UI for booking healthcare appointments.

## Run locally

1. Install dependencies:
   - `pip install -r requirements.txt`
2. Configure DB:
   - Set `DATABASE_URL` in `.env`, or create `.streamlit/secrets.toml` from `.streamlit/secrets.toml.example`.
3. Initialize and seed database:
   - `python -m db.init_db`
   - `python -m db.seed_data`
4. Start app:
   - `streamlit run streamlit_app.py`

Sample login phone numbers after seeding:
- `5551000001`
- `5551000002`
- `5551000003`

## Deploy on Streamlit Community Cloud

1. Push this project to a GitHub repository.
2. Go to [Streamlit Community Cloud](https://share.streamlit.io/) and create a new app.
3. Select:
   - Repository: your repo
   - Branch: your branch
   - Main file path: `streamlit_app.py`
4. In app settings, add this secret:
   - `DATABASE_URL = "postgresql://username:password@host:5432/database_name"`
5. Deploy.

## Notes

- The Streamlit app is text-first (no microphone/audio dependency), so it deploys cleanly on cloud.
- Booking writes to the `appointments` table and marks the selected slot as booked.
