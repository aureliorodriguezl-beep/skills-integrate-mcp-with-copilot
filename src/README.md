# Mergington High School Activities API

A super simple FastAPI application that allows students to view and sign up for extracurricular activities.

## Features

- View all available extracurricular activities
- View participant lists without signing in
- Teacher login to sign up or unregister students

## Getting Started

1. Install the dependencies:

   ```
   pip install fastapi uvicorn
   ```

2. Run the application:

   ```
   python app.py
   ```

3. Open your browser and go to:
   - API documentation: http://localhost:8000/docs
   - Alternative documentation: http://localhost:8000/redoc

## Teacher login setup

Teacher accounts are assigned by school staff; there is no public registration or account-maintenance page. Credentials are stored locally in `src/teachers.json`, which is ignored by Git. Start by copying the example file:

```sh
cp src/teachers.example.json src/teachers.json
```

Add each teacher to the `teachers` array with a unique salt and a PBKDF2-HMAC-SHA256 password hash. Generate a record without putting the password in shell history by running:

```sh
python -c 'import getpass, hashlib, json, secrets; username=input("Username: "); password=getpass.getpass("Password: "); salt=secrets.token_bytes(16); print(json.dumps({"username": username, "salt": salt.hex(), "password_hash": hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 310000).hex()}, indent=2))'
```

Paste the generated object into the `teachers` array. The API accepts the optional `TEACHER_CREDENTIALS_FILE` environment variable to load the file from another location. Teacher sessions expire after eight hours and are held only in server memory; restarting the server invalidates them. Use HTTPS in production because login credentials are sent to the server.

## API Endpoints

| Method | Endpoint                                                          | Description                                                         |
| ------ | ----------------------------------------------------------------- | ------------------------------------------------------------------- |
| GET    | `/activities`                                                     | Get all activities with their details and current participant count |
| POST   | `/auth/login`                                                      | Sign in as a teacher and receive a bearer token                     |
| POST   | `/auth/logout`                                                     | Revoke the current teacher session                                  |
| POST   | `/activities/{activity_name}/signup?email=student@mergington.edu` | Sign up a student (teacher token required)                          |
| DELETE | `/activities/{activity_name}/unregister?email=student@mergington.edu` | Unregister a student (teacher token required)                    |

## Data Model

The application uses a simple data model with meaningful identifiers:

1. **Activities** - Uses activity name as identifier:

   - Description
   - Schedule
   - Maximum number of participants allowed
   - List of student emails who are signed up

2. **Students** - Uses email as identifier:
   - Name
   - Grade level

All data is stored in memory, which means data will be reset when the server restarts.
