from datetime import datetime

current_datetime = datetime.now()

formatted_time = current_datetime.strftime("%d.%m.%y %H.%M")

print(formatted_time)