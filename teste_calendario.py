import streamlit as st
import streamlit.components.v1 as components
import json

eventos = [
    {"title": "Evento 1", "start": "2025-07-15T10:00:00", "end": "2025-07-15T11:00:00", "color": "#007bff"},
    {"title": "Evento 2", "start": "2025-07-16T14:00:00", "end": "2025-07-16T15:30:00", "color": "#28a745"}
]

eventos_js = json.dumps(eventos)

html_code = f"""
<div id='calendar'></div>
<link href='https://cdn.jsdelivr.net/npm/fullcalendar@6.1.4/index.global.min.css' rel='stylesheet' />
<script src='https://cdn.jsdelivr.net/npm/fullcalendar@6.1.4/index.global.min.js'></script>
<script>
    document.addEventListener('DOMContentLoaded', function () {{
        var calendarEl = document.getElementById('calendar');
        if (calendarEl) {{
            var calendar = new FullCalendar.Calendar(calendarEl, {{
                initialView: 'dayGridMonth',
                locale: 'pt-br',
                height: 650,
                headerToolbar: {{
                    left: 'prev,next today',
                    center: 'title',
                    right: 'dayGridMonth,timeGridWeek,timeGridDay'
                }},
                events: {eventos_js}
            }});
            calendar.render();
        }}
    }});
</script>
"""

components.html(html_code, height=700)
