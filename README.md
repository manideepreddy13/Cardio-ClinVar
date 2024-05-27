# Cardio-ClinVar

## HOW TO RUN THE APPLICATION?


1. Create a local ENV for the project and run it.
   
   Run the below commands if the system is Windows:

```bash
pip install virtualenv
virtualenv <env_name>
.\<env_name>\Scripts\activate.bat (or) .\<env_name>\Scripts\activate.ps1
```

   If the system is Linux, run the below commands:

```linux
pip install virtualenv
virtualenv <env_name>
source <env_name>/bin/activate
```

2. Now that the ENV is activated, initiate flask variables to run the project.

```
export FLASK_APP="cardio_clinvar"
export FLASK_ENV=development
flask run
```

3. In the terminal, you will receive the localhost link to the website.


## HOW TO SET SECRET KEY FOR GOOGLE AUTHENTICATION?

1. Head to [Google Console](https://console.cloud.google.com/).
2. Create a new project and name it.
3. Within the new project, navigate to APIs + Services dashboard.
4. Go to Configure Consent screen and select External Users.
5. Fill in the required fields like App name, User support email etc and add scopes if necessary.
6. Create Test users if you would like.
7. Go back to the API + Services dashboard.
8. Go to Credentials.
9. Click on Create Credentials.
10. Select OAuth Client ID.
11. Select Web App.
12. Define your redirect URL of your project (example : http://localhost:127.0.0.1/callback).
13. Create the call back and download your credentials as JSON file.
14. Now you can use this file 'client_secret.json' file in your project.
