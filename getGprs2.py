import serial
import time

# Открываем последовательный порт
ser = serial.Serial('/dev/ttyS0', baudrate=115200, timeout=1)

# Включаем GPS
ser.write(b'AT+CGNSPWR=1\r\n')
time.sleep(2)  # Даем время на выполнение команды

# Запрос данных GPS
ser.write(b'AT+CGNSINF\r\n')
time.sleep(2)  # Даем время на выполнение команды

# Чтение ответа
response = ser.read_all()
print("Raw GPS data:", response)  # Выводим сырые данные для дебага

# Обработка данных
if "+CGNSINF:" in response.decode():
    data = response.decode().split(",")  # Разделяем данные по запятым
    if len(data) >= 7:
        status = data[1]  # Статус GPS: 1 - активен
        latitude = data[3]  # Широта
        longitude = data[4]  # Долгота
        if status == '1':  # Убедимся, что GPS активен
            print(f"Latitude: {latitude}, Longitude: {longitude}")
        else:
            print("GPS is not active")
else:
    print("No GPS data found")

# Закрываем порт
ser.close()
