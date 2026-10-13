# llm.py
import os
import requests
import json

YANDEX_API_KEY = os.getenv("YANDEX_API_KEY", "")
YANDEX_FOLDER_ID = os.getenv("YANDEX_FOLDER_ID", "")

API_URL = "https://llm.api.cloud.yandex.net/foundationModels/v1/completion"
MODEL_URI = f"gpt://{YANDEX_FOLDER_ID}/yandexgpt-lite/latest"

def generate_bia_report_with_llm(risk_data: dict, bia_data: dict, answers: dict) -> list:
    """
    Генерирует BIA-отчёт через LLM.
    Возвращает список рекомендаций с учётом MTPD/RTO/RPO.
    """
    
    if not YANDEX_API_KEY or not YANDEX_FOLDER_ID:
        return _fallback_bia_recommendations(bia_data, answers)
    
    system_prompt = """Ты — эксперт по непрерывности бизнеса (Business Continuity) и кибербезопасности.
Ты проводишь Business Impact Analysis для компании, которая зависит от облачных провайдеров.
Пиши на русском. Будь конкретным: называй сроки, приоритеты, альтернативных провайдеров.
Отвечай в формате JSON: {"recommendations": ["шаг 1", "шаг 2", ...]}
Не добавляй ничего кроме JSON."""

    user_prompt = f"""Проведи Business Impact Analysis для компании.

Результаты оценки риска:
- Уровень: {risk_data['risk_level']} ({risk_data['percentage']}%)
- Баллы: {risk_data['score']}/{risk_data['max_score']}

Данные BIA:
- MTPD (максимально допустимый простой): {bia_data['mtpd']['label']}
- RTO (целевое время восстановления): {bia_data['rto_hours']} ч
- RPO (допустимая потеря данных): {bia_data['rpo_hours']} ч
- Оценка потерь: {bia_data['loss_per_hour']} ₽/час
- Общие потери при MTPD: {bia_data['total_loss']} ₽

Ответы компании:
- Провайдеров: {answers.get('providers')}
- Резерв: {answers.get('failover')}
- Данные: {answers.get('data_location')}
- GPU: {answers.get('gpu')}

Дай 4-6 рекомендаций по обеспечению непрерывности бизнеса.
Для каждой укажи:
1. Что сделать
2. Почему это критично (с учётом MTPD/RTO)
3. Примерный срок и стоимость"""

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Api-Key {YANDEX_API_KEY}"
    }

    payload = {
        "modelUri": MODEL_URI,
        "completionOptions": {
            "stream": False,
            "temperature": 0.3,
            "maxTokens": 1200
        },
        "messages": [
            {"role": "system", "text": system_prompt},
            {"role": "user", "text": user_prompt}
        ]
    }

    try:
        response = requests.post(API_URL, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        data = response.json()
        llm_text = data["result"]["alternatives"][0]["message"]["text"]
        
        cleaned = llm_text.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("```")[1]
            if cleaned.startswith("json"):
                cleaned = cleaned[4:]
        
        parsed = json.loads(cleaned)
        return parsed.get("recommendations", [])
        
    except Exception as e:
        print(f"[LLM ERROR] {e}")
        return _fallback_bia_recommendations(bia_data, answers)


def _fallback_bia_recommendations(bia_data: dict, answers: dict) -> list:
    """BIA-рекомендации без LLM."""
    recs = []
    
    if bia_data["rto_hours"] > bia_data["mtpd"]["mtpd_hours"]:
        recs.append(
            f"КРИТИЧНО: Ваше целевое время восстановления ({bia_data['rto_hours']} ч) "
            f"превышает допустимый простой ({bia_data['mtpd']['label']}). "
            f"Необходимо срочно сократить RTO."
        )
    
    if answers.get("providers") == "one":
        recs.append(
            f"Заключите договор с резервным провайдером. При MTPD {bia_data['mtpd']['label']} "
            f"у вас нет времени на поиск альтернативы после сбоя."
        )
    
    if answers.get("failover") == "no":
        recs.append(
            f"Настройте автоматический failover. Это сократит RTO с {bia_data['rto_hours']} ч "
            f"до ~1 ч и уложится в MTPD."
        )
    
    if answers.get("data_location") == "single_cloud":
        recs.append(
            f"Настройте бэкап за пределы основного облака. RPO {bia_data['rpo_hours']} ч "
            f"означает возможную потерю данных за последние часы."
        )
    
    if answers.get("gpu") == "yes_critical":
        recs.append(
            "Для GPU-нагрузок рассмотрите резервный GPU-кластер. Потери при простое "
            f"оцениваются в {bia_data['loss_per_hour']} ₽/час."
        )
    
    if not recs:
        recs.append(
            f"Ваша архитектура укладывается в MTPD. Проведите тестовое отключение "
            f"одного провайдера, чтобы проверить RTO на практике."
        )
    
    return recs