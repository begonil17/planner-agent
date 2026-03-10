import json
import sqlite3
import uuid
import webbrowser
from contextlib import contextmanager
from pathlib import Path
from agents import function_tool

BASE_DIR = Path(__file__).parent
CALENDAR_DB   = BASE_DIR / "calendar.db"
CALENDAR_HTML = BASE_DIR / "calendar.html"


# ---------------------------------------------------------------------------
# Database helpers
# ---------------------------------------------------------------------------

@contextmanager
def _db():
    """Open a SQLite connection with WAL mode (safe for concurrent writes)."""
    conn = sqlite3.connect(str(CALENDAR_DB), timeout=10, check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def _ensure_calendar_initialized() -> None:
    """Create the events table and initial calendar.html if they don't exist."""
    with _db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS events (
                id          TEXT PRIMARY KEY,
                date        TEXT NOT NULL,
                time        TEXT NOT NULL DEFAULT '',
                title       TEXT NOT NULL,
                description TEXT NOT NULL DEFAULT ''
            )
        """)
    if not CALENDAR_HTML.exists():
        _regenerate_html()


def _all_events() -> list[dict]:
    """Return all events as a list of dicts, sorted by date then time."""
    with _db() as conn:
        rows = conn.execute(
            "SELECT id, date, time, title, description FROM events ORDER BY date, time"
        ).fetchall()
    return [dict(r) for r in rows]


def _regenerate_html() -> None:
    events_json = json.dumps(_all_events(), ensure_ascii=False)
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Student Calendar</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Noto+Sans+Mono:wght@100..900&display=swap" rel="stylesheet">
  <style>
    *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      font-family: 'Noto Sans Mono', monospace;
      background: #08082e;
      color: #FAF9F6;
      min-height: 100vh;
      padding: 24px 16px;
    }}
    h1 {{
      text-align: center;
      font-size: 1.75rem;
      font-weight: 700;
      margin-bottom: 20px;
      color: #FAF9F6;
    }}
    .container {{ max-width: 900px; margin: 0 auto; }}
    .nav {{
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 20px;
      margin-bottom: 16px;
    }}
    .nav button {{
      background: #2a2a70;
      color: #c8c8e8;
      border: none;
      border-radius: 8px;
      padding: 8px 18px;
      font-size: 1rem;
      cursor: pointer;
      transition: background .2s;
    }}
    .nav button:hover {{ background: #353585; }}
    #month-label {{
      font-size: 1.3rem;
      font-weight: 600;
      min-width: 180px;
      text-align: center;
      color: #FAF9F6;
    }}
    .grid {{
      display: grid;
      grid-template-columns: repeat(7, 1fr);
      gap: 6px;
      background: #0d0d35;
      border-radius: 16px;
      padding: 16px;
    }}
    .day-header {{
      text-align: center;
      font-size: .75rem;
      font-weight: 600;
      text-transform: uppercase;
      color: #7070a0;
      padding: 6px 0;
    }}
    .day {{
      min-height: 80px;
      border-radius: 10px;
      padding: 6px;
      background: #121230;
      border: 1px solid #1e1e50;
      cursor: pointer;
      transition: background .15s;
    }}
    .day:hover {{ background: #1a1a40; border-color: #353585; }}
    .day.today {{ background: #252560; border-color: #5050a0; }}
    .day.empty {{ background: transparent; border-color: transparent; cursor: default; }}
    .day-num {{ font-size: .85rem; font-weight: 600; color: #c8c8e8; }}
    .day.today .day-num {{ color: #a0a0d0; }}
    .event-dot {{
      display: block;
      background: #4040a0;
      color: #c8c8e8;
      border-radius: 4px;
      font-size: .68rem;
      padding: 2px 5px;
      margin-top: 3px;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }}
    .events-section {{
      background: #0d0d35;
      border-radius: 16px;
      padding: 20px;
      margin-top: 20px;
      box-shadow: 0 2px 12px rgba(0,0,0,.5);
    }}
    .events-section h2 {{
      font-size: 1.1rem;
      font-weight: 600;
      margin-bottom: 14px;
      color: #8080b0;
    }}
    .event-card {{
      border-left: 4px solid #4040a0;
      background: #121230;
      border-radius: 0 8px 8px 0;
      padding: 10px 14px;
      margin-bottom: 10px;
    }}
    .event-card .event-title {{ font-weight: 600; font-size: .95rem; color: #c8c8e8; }}
    .event-card .event-meta {{ font-size: .8rem; color: #7070a0; margin-top: 2px; }}
    .event-card .event-desc {{ font-size: .85rem; margin-top: 4px; color: #a0a0c0; }}
    .no-events {{ color: #7070a0; font-size: .9rem; text-align: center; padding: 16px; }}
    .modal-overlay {{
      display: none;
      position: fixed; inset: 0;
      background: rgba(0,0,0,.7);
      z-index: 100;
      align-items: center;
      justify-content: center;
    }}
    .modal-overlay.open {{ display: flex; }}
    .modal {{
      background: #0d0d35;
      border: 1px solid #1e1e50;
      border-radius: 14px;
      padding: 24px;
      min-width: 320px;
      max-width: 480px;
      width: 90%;
      box-shadow: 0 8px 32px rgba(0,0,0,.6);
      color: #c8c8e8;
    }}
    .modal h3 {{ font-size: 1.1rem; font-weight: 600; margin-bottom: 14px; color: #c8c8e8; }}
    .modal .close-btn {{
      float: right;
      background: none;
      border: none;
      font-size: 1.4rem;
      cursor: pointer;
      color: #7070a0;
    }}
  </style>
</head>
<body>
  <div class="container">
    <h1>Student Calendar</h1>
    <div class="nav">
      <button onclick="navigate(-1)">&#9664; Prev</button>
      <span id="month-label"></span>
      <button onclick="navigate(1)">Next &#9654;</button>
    </div>
    <div class="grid" id="calendar-grid"></div>
    <div class="events-section">
      <h2>Upcoming Events</h2>
      <div id="events-list"></div>
    </div>
  </div>

  <div class="modal-overlay" id="modal" onclick="closeModal(event)">
    <div class="modal">
      <button class="close-btn" onclick="document.getElementById('modal').classList.remove('open')">&#10005;</button>
      <h3 id="modal-date"></h3>
      <div id="modal-events"></div>
    </div>
  </div>

  <script>
    const ALL_EVENTS = {events_json};
    const DAYS   = ['Sun','Mon','Tue','Wed','Thu','Fri','Sat'];
    const MONTHS = ['January','February','March','April','May','June',
                    'July','August','September','October','November','December'];
    let current = new Date();
    let viewYear = current.getFullYear(), viewMonth = current.getMonth();

    function eventsForDate(y,m,d) {{
      const key = `${{y}}-${{String(m+1).padStart(2,'0')}}-${{String(d).padStart(2,'0')}}`;
      return ALL_EVENTS.filter(e => e.date === key);
    }}
    function renderCalendar() {{
      const grid = document.getElementById('calendar-grid');
      grid.innerHTML = '';
      document.getElementById('month-label').textContent = MONTHS[viewMonth]+' '+viewYear;
      DAYS.forEach(d => {{ const h=document.createElement('div'); h.className='day-header'; h.textContent=d; grid.appendChild(h); }});
      const first = new Date(viewYear,viewMonth,1).getDay();
      const total = new Date(viewYear,viewMonth+1,0).getDate();
      for(let i=0;i<first;i++){{ const e=document.createElement('div'); e.className='day empty'; grid.appendChild(e); }}
      const todayStr=`${{current.getFullYear()}}-${{String(current.getMonth()+1).padStart(2,'0')}}-${{String(current.getDate()).padStart(2,'0')}}`;
      for(let d=1;d<=total;d++){{
        const cell=document.createElement('div'); cell.className='day';
        const dateStr=`${{viewYear}}-${{String(viewMonth+1).padStart(2,'0')}}-${{String(d).padStart(2,'0')}}`;
        if(dateStr===todayStr) cell.classList.add('today');
        const num=document.createElement('span'); num.className='day-num'; num.textContent=d; cell.appendChild(num);
        const evts=eventsForDate(viewYear,viewMonth,d);
        evts.slice(0,3).forEach(ev=>{{ const dot=document.createElement('span'); dot.className='event-dot'; dot.textContent=(ev.time?ev.time+' ':'')+ev.title; cell.appendChild(dot); }});
        if(evts.length>3){{ const more=document.createElement('span'); more.className='event-dot'; more.style.background='#94a3b8'; more.textContent=`+${{evts.length-3}} more`; cell.appendChild(more); }}
        cell.onclick=()=>openModal(dateStr,evts); grid.appendChild(cell);
      }}
    }}
    function renderUpcoming() {{
      const container=document.getElementById('events-list'); container.innerHTML='';
      const todayStr=`${{current.getFullYear()}}-${{String(current.getMonth()+1).padStart(2,'0')}}-${{String(current.getDate()).padStart(2,'0')}}`;
      const upcoming=ALL_EVENTS.filter(e=>e.date>=todayStr).sort((a,b)=>(a.date+(a.time||'')).localeCompare(b.date+(b.time||''))).slice(0,20);
      if(!upcoming.length){{ container.innerHTML='<p class="no-events">No upcoming events.</p>'; return; }}
      upcoming.forEach(ev=>{{ const card=document.createElement('div'); card.className='event-card';
        card.innerHTML=`<div class="event-title">${{ev.title}}</div><div class="event-meta">${{ev.date}}${{ev.time?' &bull; '+ev.time:''}} &bull; ID: ${{ev.id}}</div>${{ev.description?'<div class="event-desc">'+ev.description+'</div>':''}}`; container.appendChild(card); }});
    }}
    function navigate(dir){{ viewMonth+=dir; if(viewMonth>11){{viewMonth=0;viewYear++;}} if(viewMonth<0){{viewMonth=11;viewYear--;}} renderCalendar(); }}
    function openModal(dateStr,evts){{
      document.getElementById('modal-date').textContent=dateStr;
      const body=document.getElementById('modal-events'); body.innerHTML='';
      if(!evts.length){{ body.innerHTML='<p style="color:#94a3b8">No events on this day.</p>'; }}
      else{{ evts.forEach(ev=>{{ body.innerHTML+=`<div class="event-card" style="margin-top:10px"><div class="event-title">${{ev.title}}</div><div class="event-meta">${{ev.time||'All day'}} &bull; ID: ${{ev.id}}</div>${{ev.description?'<div class="event-desc">'+ev.description+'</div>':''}}</div>`; }}); }}
      document.getElementById('modal').classList.add('open');
    }}
    function closeModal(e){{ if(e.target.id==='modal') document.getElementById('modal').classList.remove('open'); }}
    renderCalendar(); renderUpcoming();
  </script>
</body>
</html>"""
    with open(CALENDAR_HTML, "w", encoding="utf-8") as f:
        f.write(html)

@function_tool
def add_calendar_event(date: str, title: str, description: str, time: str = ""):
    """Add an event to the student calendar. 'date' must be in YYYY-MM-DD format.
    'time' is optional (HH:MM, 24-hour). Returns confirmation with the new event ID.
    The calendar.html file is automatically updated."""
    event_id = str(uuid.uuid4())[:8]
    with _db() as conn:
        conn.execute(
            "INSERT INTO events (id, date, time, title, description) VALUES (?,?,?,?,?)",
            (event_id, date, time, title, description),
        )
    _regenerate_html()
    return (
        f"Event added successfully.\n"
        f"  ID: {event_id}\n"
        f"  Date: {date}{' at ' + time if time else ''}\n"
        f"  Title: {title}\n"
        f"Calendar updated — open calendar.html to view."
    )


@function_tool
def update_calendar_event(event_id: str, date: str = "", title: str = "",
                           description: str = "", time: str = ""):
    """Update an existing calendar event by its ID. Only supply fields you want to change.
    The calendar.html file is automatically regenerated."""
    fields, values = [], []
    if date:        fields.append("date=?");        values.append(date)
    if title:       fields.append("title=?");       values.append(title)
    if description: fields.append("description=?"); values.append(description)
    if time:        fields.append("time=?");        values.append(time)
    if not fields:
        return "Nothing to update — no fields provided."
    values.append(event_id)
    with _db() as conn:
        cur = conn.execute(f"UPDATE events SET {', '.join(fields)} WHERE id=?", values)
        if cur.rowcount == 0:
            return f"No event found with ID '{event_id}'."
    _regenerate_html()
    return f"Event '{event_id}' updated. Calendar regenerated."


@function_tool
def remove_calendar_event(event_id: str):
    """Remove a calendar event by its ID. The calendar.html file is automatically regenerated."""
    with _db() as conn:
        cur = conn.execute("DELETE FROM events WHERE id=?", (event_id,))
        if cur.rowcount == 0:
            return f"No event found with ID '{event_id}'."
    _regenerate_html()
    return f"Event '{event_id}' removed. Calendar updated."


@function_tool
def list_calendar_events():
    """List all events currently in the student calendar, sorted by date and time."""
    events = _all_events()
    if not events:
        return "The calendar is empty — no events have been added yet."
    lines = [
        f"[{e['id']}] {e['date']}{' at ' + e['time'] if e['time'] else ''} | {e['title']} — {e['description']}"
        for e in events
    ]
    return "\n".join(lines)


@function_tool
def open_calendar():
    """Open the student calendar HTML file in the default web browser."""
    _regenerate_html()
    webbrowser.open(CALENDAR_HTML.as_uri())
    return f"Calendar opened in browser: {CALENDAR_HTML}"


# Initialise DB table and HTML on module load
_ensure_calendar_initialized()
