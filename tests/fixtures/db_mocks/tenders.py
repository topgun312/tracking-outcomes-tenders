from uuid import UUID

TENDERS = (
    {
        "id": UUID("3d3e784f-646a-4ad4-979c-dca5dcea2a28"),
        "title": "Поставка оборудования",
        "description": "Закупка серверов",
        "status": "active",
        "customer": "ООО Ромашка",
    },
    {
        "id": UUID("bb929d29-a8ef-4a8e-b998-9998984d8fd6"),
        "title": "Ремонт офиса",
        "description": None,
        "status": "won",
        "customer": "ООО Пример",
    },
    {
        "id": UUID("d5621653-f72b-4124-98e6-79c5d9c2dc2b"),
        "title": "Закупка ПО",
        "description": "Лицензии",
        "status": "draft",
        "customer": None,
    },
)

TENDER_STATUS_HISTORY = (
    {
        "id": UUID("e4f21ac0-8b40-4f2a-9c1e-5b0d4e3a2a01"),
        "tender_id": UUID("3d3e784f-646a-4ad4-979c-dca5dcea2a28"),
        "old_status": "draft",
        "new_status": "active",
        "changed_by": "system",
        "reason": "Тендер опубликован",
    },
    {
        "id": UUID("e4f21ac0-8b40-4f2a-9c1e-5b0d4e3a2a02"),
        "tender_id": UUID("bb929d29-a8ef-4a8e-b998-9998984d8fd6"),
        "old_status": "draft",
        "new_status": "active",
        "changed_by": "system",
        "reason": "Тендер опубликован",
    },
    {
        "id": UUID("e4f21ac0-8b40-4f2a-9c1e-5b0d4e3a2a03"),
        "tender_id": UUID("bb929d29-a8ef-4a8e-b998-9998984d8fd6"),
        "old_status": "active",
        "new_status": "won",
        "changed_by": "admin",
        "reason": "Победа в тендере",
    },
    {
        "id": UUID("e4f21ac0-8b40-4f2a-9c1e-5b0d4e3a2a04"),
        "tender_id": UUID("d5621653-f72b-4124-98e6-79c5d9c2dc2b"),
        "old_status": "draft",
        "new_status": "draft",
        "changed_by": "system",
        "reason": "Тендер создан",
    },
)
