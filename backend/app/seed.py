from datetime import date
from sqlalchemy import select
from .db import Base, SessionLocal, engine
from .models import HealthRecord, Holding, Renewal, User
from .config import get_settings
from .auth import hash_password

def seed():
    Base.metadata.create_all(engine)
    db = SessionLocal()
    try:
        existing = db.scalar(select(User).where(User.email == "demo@personalos.ai"))
        if existing:
            permissions = set(existing.permissions or [])
            if "investment.execute" not in permissions:
                existing.permissions = [*permissions, "investment.execute"]
                db.commit()
            return
        db.add(User(id="user-001", name="Aarav Sharma", email="demo@personalos.ai",
                    password_hash=hash_password(get_settings().demo_password), role="user",
                    permissions=["renewal.read", "renewal.create", "renewal.update", "renewal.delete", "health.read", "health.create", "stock.read", "stock.analyze", "investment.propose", "investment.confirm", "investment.execute", "supervisor.route", "audit.read"]))
        for name, category, due, reminder, status in [("Health insurance premium","Insurance",date(2026,10,5),18,"upcoming"),("Driving licence renewal","Government",date(2026,9,25),5,"upcoming"),("Spotify Family","Subscription",date(2026,9,30),10,"upcoming"),("Vehicle insurance","Insurance",date(2026,8,14),-18,"overdue")]:
            db.add(Renewal(owner_id="user-001",name=name,category=category,due_date=due,reminder_days=reminder,status=status))
        for day, metric, value, unit in [(10,"sleep",7.2,"hours"),(11,"sleep",6.8,"hours"),(12,"sleep",7.9,"hours"),(13,"heartRate",68,"bpm"),(14,"heartRate",66,"bpm"),(15,"steps",9200,"steps"),(16,"steps",11850,"steps")]:
            db.add(HealthRecord(owner_id="user-001",date=date(2026,9,day),metric=metric,value=value,unit=unit))
        for symbol, shares, price, allocation in [("AAPL",18,214.44,24),("MSFT",12,437.1,20),("NIFTY50",96,24120,18),("RELIANCE",28,2924,16)]:
            db.add(Holding(owner_id="user-001",symbol=symbol,shares=shares,price=price,allocation=allocation))
        db.commit()
    finally: db.close()

