quickauct
quick1234

lbid
laouali1234

login
{
"email": "test@gmail.com",
"password": "test"
}

creation
{
"first_name": "test",
"last_name": "test",
"username": "test1",
"email": "test@gmail.com",
"password": "test"
}

A JSON Web Token authentication plugin for the Django REST Framework.
https://django-rest-framework-simplejwt.readthedocs.io/en/latest/

create your own .env

SECRET_KEY = ''

ENVIRONMENT= DEVELOPMENT

EMAIL_HOST = 'smtp.gmail.com'
EMAIL_HOST_USER = ''
EMAIL_HOST_PASSWORD = ''
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_USE_SSL = False

JWT_SECRET_KEY = ''
JWT_ALGORITHM = "",
ACCESS_TOKEN_EXPIRE_MINUTES =
REFRESH_TOKEN_EXPIRE_TIME =

to generate a JWT_SECRETE_KEY

> > > openssl rand -hex 32
> > > 6f476259e482ea14fa88e35faa2d2504c3727f87442517fb1de5440520fa29e2

Redis setup
https://www.youtube.com/watch?v=DLKzd3bvgt8

1. Check if Redis is Already Running
   Run the following command in Command Prompt (cmd):
   netstat -ano | findstr :6379

   from dotenv import load_dotenv
   load_dotenv() # Load before using any os.getenv()
