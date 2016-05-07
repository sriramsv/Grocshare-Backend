from gcm import *

gcm = GCM("AIzaSyD7IT1ApGdS0iHKqaKXCz1COjJgVR2neZ8")
data = {'message': 'hey Bulldog'}

reg_id = 'APA91bGCOyAk1LaUqOQ2iVycoKDHzNJFWD0XqCu3O2Rt-bmpyWM_Y5wiS2YMC2cuH4DneGkB4A6T6xh8B-iWCu3i7Yw84Vl5ndaJwBjFOJqXw9WGYk47jYHtfolaFdd1Ml_lsMiA7KU7'

gcm.plaintext_request(registration_id=reg_id, data=data)
