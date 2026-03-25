

# This file defines the default group automatically created for new users with no teams.
# Edit the values here to change the onboarding experience.

default_group = {
    "name": "Grupo de soporte a la Srta Ejemplo",
    "description": "Srta Ejemplo tiene 80 años, es alergica a la penicilina.",
    "pinned_note": "¡Bienvenida a Nurser! Este espacio es para que se dejen notas entre turnos, o cosas importantes del día",
    "activity_types": [
        {"name": "Notas",       "type": "text",         "icon": "📝"},
        {"name": "Baño",        "type": "multi_select", "options": ["Pipí", "Popó"], "icon": "🚽"},
        {"name": "Temperatura", "type": "numeric",      "icon": "🌡️"},
    ],
}