# bia.py
# Логика Business Impact Analysis.
# Считает MTPD, RTO, RPO, финансовые потери на основе ответов пользователя.

def calculate_bia(answers: dict, risk_data: dict) -> dict:
    """
    Принимает ответы пользователя и результат скоринга.
    Возвращает BIA-отчёт: MTPD, RTO, RPO, потери, последствия.
    """
    
    # --- MTPD (Maximum Tolerable Period of Disruption) ---
    # Сколько бизнес может терпеть простой, прежде чем это станет катастрофой.
    # Основано на ответе про допустимое время простоя.
    downtime_map = {
        "less_than_4h": {"mtpd_hours": 4, "label": "4 часа", "severity": "критическая"},
        "4_to_24h": {"mtpd_hours": 24, "label": "24 часа", "severity": "высокая"},
        "days": {"mtpd_hours": 72, "label": "3 дня", "severity": "средняя"},
        "weeks_ok": {"mtpd_hours": 168, "label": "1 неделя", "severity": "низкая"},
    }
    mtpd = downtime_map.get(answers.get("downtime"), {"mtpd_hours": 4, "label": "4 часа", "severity": "критическая"})
    
    # --- RTO (Recovery Time Objective) ---
    # Целевое время восстановления. Обычно 20-30% от MTPD.
    # Если у компании есть hot-failover — RTO минимальный.
    if answers.get("failover") == "hot":
        rto_hours = 1  # автоматическое переключение
        rto_note = "Автоматический failover позволяет восстановиться за ~1 час."
    elif answers.get("failover") == "cold":
        rto_hours = 24  # холодный резерв — ручной запуск
        rto_note = "«Холодный» резерв требует ручного запуска — восстановление займёт до 24 часов."
    else:
        rto_hours = 72  # нет резерва — ищем провайдера, мигрируем
        rto_note = "Без резервного провайдера восстановление может занять дни."
    
    # --- RPO (Recovery Point Objective) ---
    # Сколько данных можно потерять. Зависит от того, где хранятся данные.
    if answers.get("data_location") == "on_prem_backup":
        rpo_hours = 24  # ежедневный бэкап
        rpo_note = "Локальный бэкап позволяет терять не более суток данных."
    elif answers.get("data_location") == "multi_cloud":
        rpo_hours = 1  # репликация между облаками
        rpo_note = "Репликация между облаками минимизирует потерю данных."
    else:
        rpo_hours = 4  # данные в одном облаке — потеря зависит от провайдера
        rpo_note = "При сбое провайдера возможна потеря данных за последние часы."
    
    # --- Финансовые потери ---
    # Грубая оценка. Реальные цифры клиент должен подставить свои.
    # Если ML-нагрузки критичны — потери выше.
    base_loss_per_hour = 50000  # ₽/час — усреднённая оценка для МСБ
    
    if answers.get("gpu") == "yes_critical":
        base_loss_per_hour = 150000  # GPU-нагрузки дороже
        loss_note = "Потери повышены: GPU-нагрузки критичны для бизнеса."
    else:
        loss_note = "Базовая оценка потерь для МСБ."
    
    total_loss = base_loss_per_hour * mtpd["mtpd_hours"]
    
    # --- Операционные последствия ---
    # Что именно остановится. Зависит от критичности.
    consequences = []
    if mtpd["mtpd_hours"] <= 4:
        consequences = [
            "Полная остановка клиентских сервисов.",
            "Невозможность принимать заказы и платежи.",
            "Потеря доступа к критичным данным.",
            "Репутационные потери перед клиентами.",
        ]
    elif mtpd["mtpd_hours"] <= 24:
        consequences = [
            "Задержки в обработке заказов.",
            "Снижение качества клиентской поддержки.",
            "Временная потеря доступа к аналитике.",
        ]
    else:
        consequences = [
            "Замедление внутренних процессов.",
            "Возможны задержки отчётности.",
            "Ограниченный доступ к второстепенным сервисам.",
        ]
    
    return {
        "mtpd": mtpd,
        "rto_hours": rto_hours,
        "rto_note": rto_note,
        "rpo_hours": rpo_hours,
        "rpo_note": rpo_note,
        "loss_per_hour": base_loss_per_hour,
        "total_loss": total_loss,
        "loss_note": loss_note,
        "consequences": consequences,
    }