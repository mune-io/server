import boto3
import serial
import time
import atexit
import logging
from botocore.exceptions import EndpointConnectionError, ClientError

# Настройка логирования
logging.basicConfig(filename='/home/zero/gps.log', level=logging.DEBUG,
                    format='%(asctime)s %(levelname)s %(message)s')

# Функция для создания клиента DynamoDB
def create_dynamodb_client():
    aws_access_key_id = 'TK'
    aws_secret_access_key = '2htN2V2tBy7gBW7T90q'
    region_name = 'eu-north-1'

    dynamodb = boto3.resource(
        'dynamodb',
        region_name=region_name,
        aws_access_key_id=aws_access_key_id,
        aws_secret_access_key=aws_secret_access_key
    )
    return dynamodb

# Функция для загрузки данных в DynamoDB
def load_data_to_dynamodb(data, table_name):
    dynamodb = create_dynamodb_client()
    table = dynamodb.Table(table_name)
    with table.batch_writer() as batch:
        batch.put_item(Item=data)

# Функция для получения серийного номера Raspberry Pi
def get_serial_number():
    try:
        with open('/proc/cpuinfo', 'r') as f:
            for line in f:
                if line.strip().startswith('Serial'):
                    serial_number = line.split(':')[1].strip()
                    return serial_number
    except Exception as e:
        logging.error(f"Ошибка чтения серийного номера: {e}")
        return None

# Функция для инициализации GPS
def initialize_gps():
    ser = serial.Serial('/dev/ttyS0', baudrate=115200, timeout=1)
    ser.write(b'AT+CGNSPWR=1\r\n')
    time.sleep(10)  # Даем время на выполнение команды и инициализацию GPS
    return ser

# Функция для получения данных GPS
def get_gps_data(ser):
    ser.write(b'AT+CGNSINF\r\n')
    time.sleep(3)  # Даем время на выполнение команды

    response = ser.read_all()
    logging.debug("Raw GPS data: %s", response)

    if len(response) == 0:
        logging.debug("No GPS data received.")
        return None

    try:
        data = response.decode('latin1')  # Измените кодировку здесь, если требуется
        logging.debug("Decoded GPS data: %s", data)

        if '+CGNSINF:' in data:
            data = data.split(',')  # Разделяем данные по запятым
            if len(data) >= 4:
                gps_time = data[2]  # Время GPS
                latitude = data[3]  # Широта
                longitude = data[4]  # Долгота

                # Проверка корректности данных
                if latitude and longitude and latitude != '0' and longitude != '0':
                    return (gps_time, latitude, longitude)
                else:
                    logging.debug("Invalid GPS data")
            else:
                logging.debug("GPS data is not complete")
        else:
            logging.debug("No GPS data found")
    except UnicodeDecodeError as e:
        logging.error("Decode error: %s", e)
    return None

# Функция для закрытия порта GPS
def close_gps(ser):
    logging.info("Closing GPS port...")
    ser.close()

# Основная функция
def main():
    serial_number = get_serial_number()
    if not serial_number:
        logging.error("Не удалось получить серийный номер Raspberry Pi")
        return
    logging.info("Серийный номер Raspberry Pi: %s", serial_number)

    ser = initialize_gps()
    atexit.register(close_gps, ser)  # Закрываем порт при завершении программы

    try:
        while True:
            gps_data = get_gps_data(ser)
            if gps_data:
                gps_time, latitude, longitude = gps_data
                logging.info(f"Latitude: {latitude}, Longitude: {longitude}")
                data = {
                    "table_num": serial_number,
                    "time": gps_time,  # Используем время из GPS данных
                    "GPRS": f"{latitude},{longitude}"
                }
                table_name = 'gprs_tab1'  # Замените 'gprs_tab1' на имя вашей таблицы DynamoDB
                attempt = 0
                while attempt < 5:
                    try:
                        load_data_to_dynamodb(data, table_name)
                        logging.info("Data loaded successfully into DynamoDB table.")
                        break
                    except (EndpointConnectionError, ClientError) as e:
                        attempt += 1
                        wait_time = 2 ** attempt
                        logging.error(f"Attempt {attempt} failed: {e}. Retrying in {wait_time} seconds.")
                        time.sleep(wait_time)
            else:
                logging.info("Failed to get GPS data")
            time.sleep(10)  # Ждем 10 секунд перед следующим запросом
    except KeyboardInterrupt:
        logging.info("Terminating the program")

if __name__ == "__main__":
    logging.info("Starting GPS script")
    main()
    logging.info("Closing GPS script")
