# main.py
from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, Response
from fastapi.templating import Jinja2Templates

from llm import generate_bia_report_with_llm
from pdf_export import generate_report_pdf
from bia import calculate_bia

app = FastAPI(title="Cloud Dependency Audit")
templates = Jinja2Templates(directory="templates")


def calculate_dependency_score(answers: dict) -> dict:
    score = 0
    max_score = 0
    details = []

    max_score += 30
    providers = answers.get("providers")
    if providers == "one":
        score += 30
        details.append("Вы используете одного облачного провайдера — это критический риск.")
    elif providers == "two":
        score += 15
        details.append("Два провайдера — лучше, чем один, но всё ещё есть зависимость.")
    elif providers == "three_plus":
        details.append("Три и более провайдера — хорошая устойчивость.")
    else:
        score += 30

    max_score += 25
    failover = answers.get("failover")
    if failover == "no":
        score += 25
        details.append("Нет активного резервного провайдера — при сбое вы остановитесь полностью.")
    elif failover == "cold":
        score += 15
        details.append("Резерв есть, но он «холодный» (запуск вручную). Это займёт дни.")
    elif failover == "hot":
        details.append("Активный резерв — это правильная архитектура.")
    else:
        score += 25

    max_score += 20
    data_location = answers.get("data_location")
    if data_location == "single_cloud":
        score += 20
        details.append("Критичные данные в одном облаке — риск потери при длительном сбое.")
    elif data_location == "multi_cloud":
        score += 10
        details.append("Данные распределены, но не полностью.")
    elif data_location == "on_prem_backup":
        details.append("Есть локальный бэкап критичных данных — это снижает риск.")
    else:
        score += 20

    max_score += 15
    downtime = answers.get("downtime")
    if downtime == "less_than_4h":
        score += 15
        details.append("Вы не переживёте даже 4 часа простоя — это очень высокий риск.")
    elif downtime == "4_to_24h":
        score += 10
        details.append("Сутки простоя — серьёзный удар по бизнесу.")
    elif downtime == "days":
        score += 5
        details.append("Вы можете пережить дни простоя, но это всё равно больно.")
    elif downtime == "weeks_ok":
        details.append("Вы устойчивы к длительным сбоям.")
    else:
        score += 15

    max_score += 10
    gpu = answers.get("gpu")
    if gpu == "yes_critical":
        score += 10
        details.append("GPU-нагрузки критичны для вас. Переезд на другой провайдер может быть долгим и дорогим.")
    elif gpu == "yes_noncritical":
        score += 5
    elif gpu == "no":
        pass
    else:
        score += 10

    percentage = (score / max_score) * 100 if max_score > 0 else 0

    if percentage >= 70:
        risk_level = "КРИТИЧЕСКИЙ"
        risk_color = "red"
    elif percentage >= 40:
        risk_level = "ВЫСОКИЙ"
        risk_color = "orange"
    elif percentage >= 20:
        risk_level = "СРЕДНИЙ"
        risk_color = "yellow"
    else:
        risk_level = "НИЗКИЙ"
        risk_color = "green"

    return {
        "score": score,
        "max_score": max_score,
        "percentage": round(percentage, 1),
        "risk_level": risk_level,
        "risk_color": risk_color,
        "details": details
    }


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request, "result": None})


@app.post("/analyze", response_class=HTMLResponse)
async def analyze(
    request: Request,
    providers: str = Form(...),
    failover: str = Form(...),
    data_location: str = Form(...),
    downtime: str = Form(...),
    gpu: str = Form(...),
):
    answers = {
        "providers": providers,
        "failover": failover,
        "data_location": data_location,
        "downtime": downtime,
        "gpu": gpu,
    }

    risk_data = calculate_dependency_score(answers)
    bia_data = calculate_bia(answers, risk_data)
    recommendations = generate_bia_report_with_llm(risk_data, bia_data, answers)

    return templates.TemplateResponse("index.html", {
        "request": request,
        "result": risk_data,
        "bia": bia_data,
        "recommendations": recommendations,
        "answers": answers,
        "show_donate": True
    })


@app.post("/download/pdf")
async def download_pdf(
    providers: str = Form(...),
    failover: str = Form(...),
    data_location: str = Form(...),
    downtime: str = Form(...),
    gpu: str = Form(...),
):
    answers = {
        "providers": providers,
        "failover": failover,
        "data_location": data_location,
        "downtime": downtime,
        "gpu": gpu,
    }

    risk_data = calculate_dependency_score(answers)
    bia_data = calculate_bia(answers, risk_data)
    from llm import _fallback_bia_recommendations
    recommendations = _fallback_bia_recommendations(bia_data, answers)

    pdf_bytes = generate_report_pdf(risk_data, recommendations, answers)

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": 'attachment; filename="cloud-audit-report.pdf"'
        }
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)