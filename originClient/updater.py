from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from originClient.scheduledRun import update_forecast
def start():
    scheduler = BackgroundScheduler()
    scheduler.add_job(update_forecast, 'interval', minutes=0.25)
    scheduler.start()