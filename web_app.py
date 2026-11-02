import sqlite3
import re
from datetime import datetime
from flask import Flask, request, jsonify, render_template_string

app = Flask(__name__)
DB_NAME = "azienda_infissi_web.db"


# ==============================================================================
# 1. DATABASE & INIZIALIZZAZIONE (Listino, Preventivi e Log di Sicurezza)
# ==============================================================================
def get_db():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS listino (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            categoria TEXT NOT NULL,
            nome TEXT NOT NULL UNIQUE,
            prezzo_base REAL NOT NULL
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS preventivi (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cliente TEXT NOT NULL,
            telefono TEXT,
            data_creazione TEXT NOT NULL,
            profilo TEXT NOT NULL,
            vetro TEXT NOT NULL,
            larghezza_mm INTEGER NOT NULL,
            altezza_mm INTEGER NOT NULL,
            ante INTEGER NOT NULL,
            quantita INTEGER NOT NULL,
            posa_inclusa INTEGER NOT NULL,
            prezzo_totale REAL NOT NULL,
            stato TEXT DEFAULT 'Preventivo'
        )
    """)

    # Tabella SIEM / Security Audit Log per i test di sicurezza
    cur.execute("""
        CREATE TABLE IF NOT EXISTS security_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            ip_address TEXT NOT NULL,
            user_agent TEXT,
            endpoint TEXT NOT NULL,
            evento TEXT NOT NULL,
            livello TEXT NOT NULL, -- INFO, WARNING, CRITICAL
            payload_sospetto TEXT
        )
    """)

    cur.execute("SELECT COUNT(*) FROM listino")
    if cur.fetchone()[0] == 0:
        voci = [
            ("Profilo", "PVC Bianco Standard", 45.0),
            ("Profilo", "PVC Effetto Legno", 58.0),
            ("Profilo", "Alluminio Taglio Termico", 75.0),
            ("Profilo", "Legno Massello Pino", 85.0),
            ("Profilo", "Legno-Alluminio Top", 110.0),
            ("Vetro", "Doppio Vetro 4/16/4 Base", 65.0),
            ("Vetro", "Doppio Vetro Basso Emissivo + Argon", 90.0),
            ("Vetro", "Triplo Vetro Isolamento Acustico/Termico", 135.0),
            ("Vetro", "Vetro Antisfondamento Blindato", 160.0)
        ]
        cur.executemany("INSERT INTO listino (categoria, nome, prezzo_base) VALUES (?, ?, ?)", voci)
    conn.commit()
    conn.close()


# ==============================================================================
# 2. MINI-WAF / RILEVATORE DI ATTACCHI (Per esercitazioni di sicurezza)
# ==============================================================================
PATTERN_ATTACCHI = [
    (r"(?i)(\bOR\b|\bAND\b).*(=|LIKE)", "Tentativo di SQL Injection (Boolean-based)"),
    (r"(?i)(UNION\s+SELECT|DROP\s+TABLE|INSERT\s+INTO|--|;)", "Tentativo di SQL Injection"),
    (r"(?i)(<script.*?>|javascript:|onerror=|onload=)", "Tentativo di Cross-Site Scripting (XSS)"),
    (r"(?i)(\.\./|\.\.\\|/etc/passwd|cmd\.exe)", "Tentativo di Path Traversal / Command Injection")
]


def registra_evento_sicurezza(ip, ua, endpoint, evento, livello="INFO", payload=""):
    conn = get_db()
    conn.execute("""
        INSERT INTO security_logs (timestamp, ip_address, user_agent, endpoint, evento, livello, payload_sospetto)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (datetime.now().strftime("%d/%m/%Y %H:%M:%S"), ip, ua, endpoint, evento, livello, payload))
    conn.commit()
    conn.close()


def ispeziona_input(dati_dict, endpoint):
    """Analizza tutti i campi inviati dal client per rilevare pattern malevoli."""
    ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    ua = request.headers.get('User-Agent', 'Sconosciuto')

    for chiave, valore in dati_dict.items():
        val_str = str(valore)
        for regex, descrizione_attacco in PATTERN_ATTACCHI:
            if re.search(regex, val_str):
                registra_evento_sicurezza(
                    ip, ua, endpoint,
                    f"ALLARME WAF: {descrizione_attacco} sul campo '{chiave}'",
                    livello="CRITICAL",
                    payload=val_str
                )
                return False, descrizione_attacco
    return True, None


# ==============================================================================
# 3. MOTORE DI CALCOLO INGEGNERISTICO
# ==============================================================================
def calcola_preventivo_core(larg_mm, alt_mm, costo_ml, costo_mq, ante, qta, posa):
    larg_m = larg_mm / 1000.0
    alt_m = alt_mm / 1000.0
    perimetro = (2 * (larg_m + alt_m)) + ((ante - 1) * alt_m)
    area_reale = larg_m * alt_m
    area_fatturabile = max(area_reale, 1.2)

    costo_unitario = (perimetro * costo_ml) + (area_fatturabile * costo_mq) + (ante * 45.0)
    if posa:
        costo_unitario += 60.0

    imponibile = costo_unitario * qta
    iva = imponibile * 0.22
    totale = imponibile + iva

    return {
        "area_mq": round(area_reale, 2),
        "perimetro_m": round(perimetro, 2),
        "unitario": round(costo_unitario, 2),
        "imponibile": round(imponibile, 2),
        "iva": round(iva, 2),
        "totale": round(totale, 2)
    }


# ==============================================================================
# 4. TEMPLATE HTML/JS INTEGRATO (SPA - Single Page Application)
# ==============================================================================
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="it">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>InfissiPro Cloud ERP & Security Lab</title>
    <style>
        :root { --primary: #1e3d59; --accent: #2b579a; --bg: #f4f6f9; --danger: #dc3545; --warn: #ffc107; --ok: #28a745; }
        body { font-family: 'Segoe UI', system-ui, sans-serif; margin: 0; background: var(--bg); color: #333; }
        header { background: var(--primary); color: white; padding: 16px 24px; display: flex; justify-content: space-between; align-items: center; }
        header h1 { margin: 0; font-size: 1.3rem; }
        .container { max-width: 1200px; margin: 20px auto; padding: 0 15px; }
        .tabs { display: flex; gap: 10px; margin-bottom: 20px; }
        .tab-btn { padding: 10px 20px; border: none; background: #dce1e7; cursor: pointer; font-weight: 600; border-radius: 6px; }
        .tab-btn.active { background: var(--accent); color: white; }
        .card { background: white; border-radius: 8px; padding: 20px; box-shadow: 0 2px 8px rgba(0,0,0,0.06); margin-bottom: 20px; }
        .grid-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }
        label { display: block; font-weight: 600; margin: 10px 0 4px; font-size: 0.9rem; }
        input, select { width: 100%; padding: 9px; border: 1px solid #ccc; border-radius: 4px; box-sizing: border-box; }
        button.action { background: var(--accent); color: white; border: none; padding: 12px 18px; border-radius: 5px; font-weight: bold; cursor: pointer; width: 100%; margin-top: 15px; }
        button.danger { background: var(--danger); color: white; border: none; padding: 6px 12px; border-radius: 4px; cursor: pointer; }
        table { width: 100%; border-collapse: collapse; margin-top: 10px; font-size: 0.9rem; }
        th, td { border-bottom: 1px solid #e0e0e0; padding: 10px; text-align: left; }
        th { background: #eef1f5; }
        .badge-CRITICAL { background: var(--danger); color: white; padding: 3px 8px; border-radius: 4px; font-weight: bold; }
        .badge-INFO { background: var(--ok); color: white; padding: 3px 8px; border-radius: 4px; }
        pre { background: #1e1e1e; color: #00ff88; padding: 15px; border-radius: 6px; overflow-x: auto; font-size: 0.9rem; }
        @media (max-width: 768px) { .grid-2 { grid-template-columns: 1fr; } }
    </style>
</head>
<body>

<header>
    <h1>INFISSIPRO CLOUD ERP — Web App & Security Monitor</h1>
    <span>Connessione: HTTP/REST</span>
</header>

<div class="container">
    <div class="tabs">
        <button class="tab-btn active" onclick="mostraTab('preventivo', this)">1. Nuovo Preventivo</button>
        <button class="tab-btn" onclick="mostraTab('archivio', this)">2. Archivio Commesse</button>
        <button class="tab-btn" onclick="mostraTab('sicurezza', this)">3. SIEM / Monitor Sicurezza (WAF)</button>
    </div>

    <!-- TAB 1: CONFIGURATORE -->
    <div id="tab-preventivo" class="grid-2">
        <div class="card">
            <h3>Dati Cliente & Specifiche Infisso</h3>
            <label>Nome Cliente / Ragione Sociale * (Prova qui un test SQLi/XSS!)</label>
            <input type="text" id="cliente" placeholder="Es. Mario Rossi">

            <label>Telefono</label>
            <input type="text" id="telefono" placeholder="Es. 333 1234567">

            <label>Materiale Profilo</label>
            <select id="profilo">
                {% for nome, prezzo in profili.items() %}
                <option value="{{ nome }}">{{ nome }} (€ {{ prezzo }}/ml)</option>
                {% endfor %}
            </select>

            <label>Tipologia Vetrocamera</label>
            <select id="vetro">
                {% for nome, prezzo in vetri.items() %}
                <option value="{{ nome }}">{{ nome }} (€ {{ prezzo }}/m²)</option>
                {% endfor %}
            </select>

            <div class="grid-2">
                <div>
                    <label>Larghezza (mm)</label>
                    <input type="number" id="larghezza" value="1200" min="300" max="4000">
                </div>
                <div>
                    <label>Altezza (mm)</label>
                    <input type="number" id="altezza" value="1400" min="300" max="3500">
                </div>
            </div>

            <div class="grid-2">
                <div>
                    <label>Numero Ante</label>
                    <select id="ante"><option>1</option><option selected>2</option><option>3</option><option>4</option></select>
                </div>
                <div>
                    <label>Quantità</label>
                    <input type="number" id="quantita" value="1" min="1">
                </div>
            </div>

            <label style="margin-top:15px;">
                <input type="checkbox" id="posa" checked style="width:auto;"> Includi Posa in Opera (+60,00 €/cad)
            </label>

            <button class="action" onclick="inviaPreventivo()">CALCOLA E SALVA COMMESSA IN CLOUD</button>
        </div>

        <div class="card">
            <h3>Prospetto Tecnico-Economico Live</h3>
            <pre id="output-box">Compila i parametri a sinistra e premi il pulsante per generare il calcolo tramite l'API REST...</pre>
        </div>
    </div>

    <!-- TAB 2: ARCHIVIO -->
    <div id="tab-archivio" class="card" style="display:none;">
        <h3>Archivio Preventivi & Stato Produzione</h3>
        <table id="tabella-ordini">
            <thead>
                <tr><th>ID</th><th>Data</th><th>Cliente</th><th>Specifiche</th><th>Misure</th><th>Q.tà</th><th>Totale IVA Inc.</th><th>Azioni</th></tr>
            </thead>
            <tbody></tbody>
        </table>
    </div>

    <!-- TAB 3: MONITOR SICUREZZA -->
    <div id="tab-sicurezza" class="card" style="display:none;">
        <h3>SIEM Locale - Rilevamento Intrusioni e Audit Log</h3>
        <p style="font-size:0.9rem; color:#555;">
            Questa scheda mostra le richieste intercettate dal server. Prova a inserire nel campo <b>Nome Cliente</b> stringhe come 
            <code>' OR 1=1 --</code> oppure <code>&lt;script&gt;alert(1)&lt;/script&gt;</code> per testare il rilevamento degli attacchi.
        </p>
        <table id="tabella-logs">
            <thead>
                <tr><th>Data/Ora</th><th>IP Client</th><th>Endpoint</th><th>Livello</th><th>Evento Rilevato</th><th>Payload Sospetto</th></tr>
            </thead>
            <tbody></tbody>
        </table>
    </div>
</div>

<script>
function mostraTab(nome, btn) {
    document.getElementById('tab-preventivo').style.display = nome === 'preventivo' ? 'grid' : 'none';
    document.getElementById('tab-archivio').style.display = nome === 'archivio' ? 'block' : 'none';
    document.getElementById('tab-sicurezza').style.display = nome === 'sicurezza' ? 'block' : 'none';
    document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    if (nome === 'archivio') caricaOrdini();
    if (nome === 'sicurezza') caricaLogs();
}

async function inviaPreventivo() {
    const payload = {
        cliente: document.getElementById('cliente').value,
        telefono: document.getElementById('telefono').value,
        profilo: document.getElementById('profilo').value,
        vetro: document.getElementById('vetro').value,
        larghezza: parseInt(document.getElementById('larghezza').value),
        altezza: parseInt(document.getElementById('altezza').value),
        ante: parseInt(document.getElementById('ante').value),
        quantita: parseInt(document.getElementById('quantita').value),
        posa: document.getElementById('posa').checked
    };

    const res = await fetch('/api/preventivi', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(payload)
    });
    const data = await res.json();
    const box = document.getElementById('output-box');

    if (!res.ok) {
        box.style.color = '#ff5555';
        box.textContent = "[BLOCCO DI SICUREZZA WAF]\\n" + data.errore;
        return;
    }

    box.style.color = '#00ff88';
    box.textContent = 
`==========================================
   COMMESSA #${data.id} REGISTRATA
==========================================
Cliente:          ${payload.cliente}
Dimensioni:       ${payload.larghezza}x${payload.altezza} mm (${payload.ante} ante)
Superficie Reale: ${data.calcolo.area_mq} m²
Sviluppo Profilo: ${data.calcolo.perimetro_m} ml
------------------------------------------
Costo Unitario:   € ${data.calcolo.unitario.toFixed(2)}
Imponibile (x${payload.quantita}):  € ${data.calcolo.imponibile.toFixed(2)}
IVA (22%):        € ${data.calcolo.iva.toFixed(2)}
==========================================
TOTALE CHIAVI IN MANO: € ${data.calcolo.totale.toFixed(2)}
==========================================`;
}

async function caricaOrdini() {
    const res = await fetch('/api/preventivi');
    const ordini = await res.json();
    const tbody = document.querySelector('#tabella-ordini tbody');
    tbody.innerHTML = '';
    ordini.forEach(o => {
        tbody.innerHTML += `<tr>
            <td>#${o.id}</td>
            <td>${o.data_creazione}</td>
            <td><b>${o.cliente}</b><br><small>${o.telefono}</small></td>
            <td>${o.profilo}<br><small>${o.vetro}</small></td>
            <td>${o.larghezza_mm}x${o.altezza_mm} (${o.ante}A)</td>
            <td>${o.quantita}</td>
            <td><b>€ ${o.prezzo_totale.toFixed(2)}</b></td>
            <td><button class="danger" onclick="eliminaOrdine(${o.id})">Elimina</button></td>
        </tr>`;
    });
}

async function eliminaOrdine(id) {
    await fetch('/api/preventivi/' + id, {method: 'DELETE'});
    caricaOrdini();
}

async function caricaLogs() {
    const res = await fetch('/api/security-logs');
    const logs = await res.json();
    const tbody = document.querySelector('#tabella-logs tbody');
    tbody.innerHTML = '';
    logs.forEach(l => {
        tbody.innerHTML += `<tr>
            <td>${l.timestamp}</td>
            <td><code>${l.ip_address}</code></td>
            <td><code>${l.endpoint}</code></td>
            <td><span class="badge-${l.livello}">${l.livello}</span></td>
            <td>${l.evento}</td>
            <td><code>${l.payload_sospetto || '-'}</code></td>
        </tr>`;
    });
}
</script>
</body>
</html>
"""


# ==============================================================================
# 5. ROTTE WEB & ENDPOINT API REST
# ==============================================================================
@app.route("/")
def home():
    conn = get_db()
    profili = dict(conn.execute("SELECT nome, prezzo_base FROM listino WHERE categoria='Profilo'").fetchall())
    vetri = dict(conn.execute("SELECT nome, prezzo_base FROM listino WHERE categoria='Vetro'").fetchall())
    conn.close()
    return render_template_string(HTML_TEMPLATE, profili=profili, vetri=vetri)


@app.route("/api/preventivi", methods=["GET", "POST"])
def gestisci_preventivi():
    conn = get_db()
    ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    ua = request.headers.get('User-Agent', 'Sconosciuto')

    if request.method == "GET":
        rows = conn.execute("SELECT * FROM preventivi ORDER BY id DESC").fetchall()
        conn.close()
        return jsonify([dict(r) for r in rows])

    if request.method == "POST":
        dati = request.get_json(force=True)

        # 1. Controllo WAF contro SQLi / XSS
        sicuro, motivo = ispeziona_input(dati, "/api/preventivi")
        if not sicuro:
            conn.close()
            return jsonify({
                               "errore": f"Richiesta bloccata: rilevato {motivo}. L'evento e il tuo IP ({ip}) sono stati registrati nel SIEM."}), 403

        if not dati.get("cliente", "").strip():
            conn.close()
            return jsonify({"errore": "Il campo Nome Cliente è obbligatorio."}), 400

        # 2. Recupero prezzi da DB
        profili = dict(conn.execute("SELECT nome, prezzo_base FROM listino WHERE categoria='Profilo'").fetchall())
        vetri = dict(conn.execute("SELECT nome, prezzo_base FROM listino WHERE categoria='Vetro'").fetchall())

        ris = calcola_preventivo_core(
            int(dati["larghezza"]), int(dati["altezza"]),
            profili[dati["profilo"]], vetri[dati["vetro"]],
            int(dati["ante"]), int(dati["quantita"]), bool(dati["posa"])
        )

        cur = conn.cursor()
        cur.execute("""
            INSERT INTO preventivi (cliente, telefono, data_creazione, profilo, vetro, larghezza_mm, altezza_mm, ante, quantita, posa_inclusa, prezzo_totale)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            dati["cliente"].strip(), dati.get("telefono", ""), datetime.now().strftime("%d/%m/%Y %H:%M"),
            dati["profilo"], dati["vetro"], int(dati["larghezza"]), int(dati["altezza"]),
            int(dati["ante"]), int(dati["quantita"]), 1 if dati["posa"] else 0, ris["totale"]
        ))
        nuovo_id = cur.lastrowid
        conn.commit()
        conn.close()

        registra_evento_sicurezza(ip, ua, "POST /api/preventivi",
                                  f"Creato preventivo #{nuovo_id} per cliente '{dati['cliente']}'", "INFO")
        return jsonify({"id": nuovo_id, "calcolo": ris}), 201


@app.route("/api/preventivi/<int:id_ordine>", methods=["DELETE"])
def elimina_preventivo(id_ordine):
    ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    ua = request.headers.get('User-Agent', 'Sconosciuto')
    conn = get_db()
    conn.execute("DELETE FROM preventivi WHERE id = ?", (id_ordine,))
    conn.commit()
    conn.close()
    registra_evento_sicurezza(ip, ua, f"DELETE /api/preventivi/{id_ordine}", f"Eliminata pratica #{id_ordine}", "INFO")
    return jsonify({"status": "deleted"})


@app.route("/api/security-logs", methods=["GET"])
def get_security_logs():
    conn = get_db()
    rows = conn.execute("SELECT * FROM security_logs ORDER BY id DESC LIMIT 100").fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


if __name__ == "__main__":
    init_db()
    # host='0.0.0.0' rende il server raggiungibile anche da altri dispositivi sulla rete
    app.run(host="0.0.0.0", port=5000, debug=False)