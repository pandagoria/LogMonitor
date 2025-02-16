import asyncio
import aiosqlite
import aiofiles
import random
from datetime import datetime
from prometheus_client import start_http_server, Gauge


async def log_generation():
    feedback = [
        "Вот это скорость",
        "Жесть какая-то",
        "Ну и запросики у вас",
        "Тут такое",
        "Посмотрите-ка",
        "Круть...",
        "Вы видели этот запрос?",
        "Возьмите Надю на работу",
        "Надя быстро учится всему",
    ]
    statuses = [200, 201, 202, 204, 400, 401, 402, 404, 500]

    while True:
        statuscode = random.choice(statuses)
        status = "INFO" if statuscode < 400 else "Error"
        responset = 0 if statuscode >= 400 else random.randint(1, 500)
        date_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        async with aiofiles.open("fake_logs.txt", mode="a") as fd:
            await fd.write(
                f"{date_time} Status={status} StatusCode={statuscode} ResponseTime={responset} Message={random.choice(feedback)}\n"
            )
        await asyncio.sleep(random.randint(0, 3))


async def commit_logs_db():
    await asyncio.sleep(1)
    async with aiosqlite.connect("logs.db") as db:
        await db.execute(
            """
        CREATE TABLE IF NOT EXISTS logs (
            timestamp TEXT,
            status TEXT,
            statuscode INTEGER,
            responset INTEGER
        );
        """
        )
        await db.commit()

        async with aiofiles.open("fake_logs.txt", mode="r") as fd:
            await fd.seek(0, 2)

            while True:
                line = await fd.readline()
                if line:
                    line = line.split()
                    timestamp = line[0] + " " + line[1]
                    status = line[2].split("=")[1]
                    statuscode = int(line[3].split("=")[1])
                    responset = int(line[4].split("=")[1])

                    print(f"Read line: {line}")
                    print(f"Insert into ds: {timestamp}, {statuscode}, {responset}")

                    try:
                        await db.execute(
                            """
                            INSERT INTO logs (timestamp, status, statuscode, responset)
                            VALUES (?, ?, ?, ?)""",
                            (timestamp, status, statuscode, responset),
                        )
                        await db.commit()
                        print("Commited?")
                    except Exception as e:
                        print(f"Error: {e}")
                else:
                    print("waiting")
                    await asyncio.sleep(1)
                    print("waited")
    print("бай бай")


async def calculate_and_export():
    avg_response_time_gauge = Gauge(
        "avg_response_time", "Среднее время ответа в миллисекундах"
    )
    err_percentage_gauge = Gauge("err_percentage", "Процент ошибок")

    async with aiosqlite.connect("logs.db") as db:
        while True:
            await db.execute("""SELECT AVG(responset) FROM logs WHERE responset > 0""")
            res = await db.fetcone()[0]
            if res:
                avg_response_time_gauge.set(res)

            await db.execute(
                """SELECT (COUNT(*) * 100 ) / (SELECT COUNT(*) FROM logs WHERE statuscode > 300) as ERRORS"""
            )
            res2 = await db.fetcone()[0]
            if res2:
                err_percentage_gauge.set(res2)
            await asyncio.sleep(6)


async def main():
    try:
        await asyncio.gather(log_generation(), commit_logs_db(), calculate_and_export())
    except KeyboardInterrupt:
        print("Получен сигнал о завершении работы...")
    print("Чуть время на сессии и ресурсы")
    await asyncio.sleep(2)


if __name__ == "__main__":
    start_http_server(8000)
    asyncio.run(main())
