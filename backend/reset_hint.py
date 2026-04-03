from database import SessionLocal
import models

db = SessionLocal()
r = db.query(models.PageContent).filter(
    models.PageContent.page_key == "categories",
    models.PageContent.element_key == "activity_hint"
).first()
r.content = '\u0412\u044b \u043c\u043e\u0436\u0435\u0442\u0435 \u0432\u043a\u043b\u044e\u0447\u0438\u0442\u044c \u0443\u0447\u0451\u0442 \u043f\u043e \u0432\u0438\u0434\u0430\u043c \u0434\u0435\u044f\u0442\u0435\u043b\u044c\u043d\u043e\u0441\u0442\u0438 \u0432 <a href="settings.html">\u041d\u0430\u0441\u0442\u0440\u043e\u0439\u043a\u0430\u0445</a>'
db.commit()
db.close()
print("ok")
