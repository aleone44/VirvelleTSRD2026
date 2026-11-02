import sqlite3
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
import os


# ==============================================================================
# 1. LIVELLO DATABASE (SQLite3)
# ==============================================================================
class DatabaseInfissi:
    def __init__(self, db_name="azienda_infissi.db"):
        self.conn = sqlite3.connect(db_name)
        self.cursor = self.conn.cursor()
        self.crea_tabelle()
        self.popola_dati_iniziali()

    def crea_tabelle(self):
        # Tabella Listino Materiali e Tipologie Vetro
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS listino (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                categoria TEXT NOT NULL,      -- 'Profilo' o 'Vetro'
                nome TEXT NOT NULL UNIQUE,
                prezzo_base REAL NOT NULL     -- Euro al m2 per vetro, Euro al metro lineare per profilo
            )
        """)

        # Tabella Preventivi / Ordini
        self.cursor.execute("""
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
                stato TEXT DEFAULT 'Preventivo' -- Preventivo, In Produzione, Consegnato
            )
        """)
        self.conn.commit()

    def popola_dati_iniziali(self):
        self.cursor.execute("SELECT COUNT(*) FROM listino")
        if self.cursor.fetchone()[0] == 0:
            voci_iniziali = [
                # Profili (Prezzo al metro lineare di perimetro)
                ("Profilo", "PVC Bianco Standard", 45.0),
                ("Profilo", "PVC Effetto Legno", 58.0),
                ("Profilo", "Alluminio Taglio Termico", 75.0),
                ("Profilo", "Legno Massello Pino", 85.0),
                ("Profilo", "Legno-Alluminio Top", 110.0),
                # Vetri (Prezzo al metro quadro di superficie)
                ("Vetro", "Doppio Vetro 4/16/4 Base", 65.0),
                ("Vetro", "Doppio Vetro Basso Emissivo + Argon", 90.0),
                ("Vetro", "Triplo Vetro Isolamento Acustico/Termico", 135.0),
                ("Vetro", "Vetro Antisfondamento Blindato", 160.0)
            ]
            self.cursor.executemany(
                "INSERT INTO listino (categoria, nome, prezzo_base) VALUES (?, ?, ?)",
                voci_iniziali
            )
            self.conn.commit()

    def get_opzioni_listino(self, categoria):
        self.cursor.execute("SELECT nome, prezzo_base FROM listino WHERE categoria = ?", (categoria,))
        return dict(self.cursor.fetchall())

    def salva_preventivo(self, dati):
        query = """
            INSERT INTO preventivi (
                cliente, telefono, data_creazione, profilo, vetro,
                larghezza_mm, altezza_mm, ante, quantita, posa_inclusa, prezzo_totale, stato
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        self.cursor.execute(query, dati)
        self.conn.commit()
        return self.cursor.lastrowid

    def get_tutti_preventivi(self):
        self.cursor.execute("SELECT * FROM preventivi ORDER BY id DESC")
        return self.cursor.fetchall()

    def aggiorna_stato_ordine(self, id_ordine, nuovo_stato):
        self.cursor.execute("UPDATE preventivi SET stato = ? WHERE id = ?", (nuovo_stato, id_ordine))
        self.conn.commit()

    def elimina_preventivo(self, id_ordine):
        self.cursor.execute("DELETE FROM preventivi WHERE id = ?", (id_ordine,))
        self.conn.commit()


# ==============================================================================
# 2. MOTORE DI CALCOLO INGEGNERISTICO E COMMERCIALE
# ==============================================================================
class CalcolatoreInfissi:
    COSTO_FERRAMENTA_ANTA = 45.00  # Costo cerniere/maniglie per singola anta
    COSTO_POSA_UNITARIO = 60.00  # Costo montaggio a infisso
    MINIMO_FATTURABILE_MQ = 1.2  # Superficie minima di calcolo per il vetro

    @classmethod
    def calcola_preventivo(cls, larghezza_mm, altezza_mm, costo_ml_profilo, costo_mq_vetro, num_ante, quantita, posa):
        # Conversioni in metri
        larghezza_m = larghezza_mm / 1000.0
        altezza_m = altezza_mm / 1000.0

        # 1. Calcolo Perimetro (Telaio esterno + partizioni per ante multiple)
        perimetro_esterno = 2 * (larghezza_m + altezza_m)
        montanti_aggiuntivi = (num_ante - 1) * altezza_m
        metri_lineari_totali = perimetro_esterno + montanti_aggiuntivi
        costo_profilo = metri_lineari_totali * costo_ml_profilo

        # 2. Calcolo Superficie Vetro (con minimo fatturabile)
        area_reale_mq = larghezza_m * altezza_m
        area_fatturabile_mq = max(area_reale_mq, cls.MINIMO_FATTURABILE_MQ)
        costo_vetro = area_fatturabile_mq * costo_mq_vetro

        # 3. Costo Ferramenta e Lavorazione
        costo_ferramenta = num_ante * cls.COSTO_FERRAMENTA_ANTA

        # Costo singolo infisso finito
        costo_unitario = costo_profilo + costo_vetro + costo_ferramenta
        if posa:
            costo_unitario += cls.COSTO_POSA_UNITARIO

        # Totale complessivo (IVA 22% inclusa o scorporabile)
        imponibile_totale = costo_unitario * quantita
        iva = imponibile_totale * 0.22
        totale_ivato = imponibile_totale + iva

        return {
            "area_reale_mq": round(area_reale_mq, 2),
            "perimetro_m": round(metri_lineari_totali, 2),
            "costo_unitario": round(costo_unitario, 2),
            "imponibile": round(imponibile_totale, 2),
            "iva": round(iva, 2),
            "totale_ivato": round(totale_ivato, 2)
        }


# ==============================================================================
# 3. INTERFACCIA GRAFICA (Tkinter GUI)
# ==============================================================================
class AppGestionaleInfissi(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("InfissiPro ERP - Sistema Gestionale Serramenti")
        self.geometry("1100x700")
        self.minsize(950, 620)

        self.db = DatabaseInfissi()
        self.profili_dict = self.db.get_opzioni_listino("Profilo")
        self.vetri_dict = self.db.get_opzioni_listino("Vetro")
        self.ultimo_calcolo = None

        self.configura_stile()
        self.crea_interfaccia()
        self.aggiorna_tabella_ordini()

    def configura_stile(self):
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("TNotebook.Tab", font=("Segoe UI", 10, "bold"), padding=[12, 6])
        style.configure("Treeview.Heading", font=("Segoe UI", 9, "bold"), background="#d9d9d9")
        style.configure("Treeview", rowheight=26, font=("Segoe UI", 9))
        style.configure("Accent.TButton", font=("Segoe UI", 10, "bold"), background="#2b579a", foreground="white")

    def crea_interfaccia(self):
        # Header Aziendale
        header = tk.Frame(self, bg="#1e3d59", height=60)
        header.pack(fill="x")
        tk.Label(
            header, text="INFISSIPRO SRL - Configuratore Preventivi & Gestione Commesse",
            bg="#1e3d59", fg="white", font=("Segoe UI", 15, "bold"), pady=12
        ).pack(side="left", padx=20)

        # Notebook a Schede
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True, padx=10, pady=10)

        # Tab 1: Configuratore Nuovo Preventivo
        self.tab_preventivo = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_preventivo, text=" + Nuovo Preventivo / Commessa ")
        self.costruisci_tab_preventivo()

        # Tab 2: Registro Ordini e Produzione
        self.tab_ordini = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_ordini, text=" Archivio Preventivi & Produzione ")
        self.costruisci_tab_ordini()

    # --------------------------------------------------------------------------
    # TAB 1: CONFIGURATORE PREVENTIVO
    # --------------------------------------------------------------------------
    def costruisci_tab_preventivo(self):
        frame_main = ttk.Frame(self.tab_preventivo, padding=15)
        frame_main.pack(fill="both", expand=True)

        # Colonna Sinistra: Input Dati
        col_sx = ttk.LabelFrame(frame_main, text=" 1. Dati Cliente e Specifiche Tecniche Infisso ", padding=15)
        col_sx.pack(side="left", fill="both", expand=True, padx=(0, 10))

        # Campi Input
        ttk.Label(col_sx, text="Nome Cliente / Ragione Sociale *:").grid(row=0, column=0, sticky="w", pady=6)
        self.ent_cliente = ttk.Entry(col_sx, width=32)
        self.ent_cliente.grid(row=0, column=1, sticky="ew", pady=6, padx=5)

        ttk.Label(col_sx, text="Telefono / Contatto:").grid(row=1, column=0, sticky="w", pady=6)
        self.ent_telefono = ttk.Entry(col_sx, width=32)
        self.ent_telefono.grid(row=1, column=1, sticky="ew", pady=6, padx=5)

        ttk.Separator(col_sx, orient="horizontal").grid(row=2, column=0, columnspan=2, sticky="ew", pady=12)

        ttk.Label(col_sx, text="Materiale Profilo:").grid(row=3, column=0, sticky="w", pady=6)
        self.cmb_profilo = ttk.Combobox(col_sx, values=list(self.profili_dict.keys()), state="readonly", width=30)
        self.cmb_profilo.current(0)
        self.cmb_profilo.grid(row=3, column=1, sticky="ew", pady=6, padx=5)

        ttk.Label(col_sx, text="Tipologia Vetrocamera:").grid(row=4, column=0, sticky="w", pady=6)
        self.cmb_vetro = ttk.Combobox(col_sx, values=list(self.vetri_dict.keys()), state="readonly", width=30)
        self.cmb_vetro.current(0)
        self.cmb_vetro.grid(row=4, column=1, sticky="ew", pady=6, padx=5)

        ttk.Label(col_sx, text="Larghezza (mm) [es. 1200]:").grid(row=5, column=0, sticky="w", pady=6)
        self.spn_larghezza = ttk.Spinbox(col_sx, from_=300, to=4000, increment=50, width=15)
        self.spn_larghezza.set(1200)
        self.spn_larghezza.grid(row=5, column=1, sticky="w", pady=6, padx=5)

        ttk.Label(col_sx, text="Altezza (mm) [es. 1400]:").grid(row=6, column=0, sticky="w", pady=6)
        self.spn_altezza = ttk.Spinbox(col_sx, from_=300, to=3500, increment=50, width=15)
        self.spn_altezza.set(1400)
        self.spn_altezza.grid(row=6, column=1, sticky="w", pady=6, padx=5)

        ttk.Label(col_sx, text="Numero di Ante:").grid(row=7, column=0, sticky="w", pady=6)
        self.cmb_ante = ttk.Combobox(col_sx, values=["1", "2", "3", "4"], state="readonly", width=13)
        self.cmb_ante.current(1)
        self.cmb_ante.grid(row=7, column=1, sticky="w", pady=6, padx=5)

        ttk.Label(col_sx, text="Quantità Infissi Identici:").grid(row=8, column=0, sticky="w", pady=6)
        self.spn_quantita = ttk.Spinbox(col_sx, from_=1, to=100, width=15)
        self.spn_quantita.set(1)
        self.spn_quantita.grid(row=8, column=1, sticky="w", pady=6, padx=5)

        self.var_posa = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            col_sx, text="Includi Posa in Opera qualificata (+60,00 €/cad)", variable=self.var_posa
        ).grid(row=9, column=0, columnspan=2, sticky="w", pady=10)

        btn_calcola = ttk.Button(col_sx, text="CALCOLA PREVENTIVO", style="Accent.TButton", command=self.esegui_calcolo)
        btn_calcola.grid(row=10, column=0, columnspan=2, sticky="ew", pady=12)

        # Colonna Destra: Riepilogo ed Esportazione
        col_dx = ttk.LabelFrame(frame_main, text=" 2. Prospetto Tecnico-Economico ", padding=15)
        col_dx.pack(side="right", fill="both", expand=True)

        self.txt_riepilogo = tk.Text(col_dx, height=18, bg="#f8f9fa", font=("Consolas", 10), state="disabled", padx=10,
                                     pady=10)
        self.txt_riepilogo.pack(fill="both", expand=True, pady=(0, 10))

        frame_bottoni_dx = ttk.Frame(col_dx)
        frame_bottoni_dx.pack(fill="x")

        self.btn_salva = ttk.Button(
            frame_bottoni_dx, text="Salva in Archivio Ordini", command=self.salva_ordine_db, state="disabled"
        )
        self.btn_salva.pack(side="left", fill="x", expand=True, padx=(0, 5))

        self.btn_esporta = ttk.Button(
            frame_bottoni_dx, text="Esporta Preventivo (.TXT)", command=self.esporta_preventivo_txt, state="disabled"
        )
        self.btn_esporta.pack(side="right", fill="x", expand=True, padx=(5, 0))

    def esegui_calcolo(self):
        try:
            larg = int(self.spn_larghezza.get())
            alt = int(self.spn_altezza.get())
            ante = int(self.cmb_ante.get())
            qta = int(self.spn_quantita.get())
            if larg < 300 or alt < 300 or qta < 1:
                raise ValueError
        except ValueError:
            messagebox.showerror("Errore Dati",
                                 "Inserire valori numerici validi per dimensioni (min 300mm) e quantità.")
            return

        profilo_scelto = self.cmb_profilo.get()
        vetro_scelto = self.cmb_vetro.get()
        posa = self.var_posa.get()

        costo_ml = self.profili_dict[profilo_scelto]
        costo_mq = self.vetri_dict[vetro_scelto]

        ris = CalcolatoreInfissi.calcola_preventivo(larg, alt, costo_ml, costo_mq, ante, qta, posa)
        self.ultimo_calcolo = {
            "cliente": self.ent_cliente.get().strip() or "Cliente Generico",
            "telefono": self.ent_telefono.get().strip() or "N/D",
            "profilo": profilo_scelto,
            "vetro": vetro_scelto,
            "larghezza": larg,
            "altezza": alt,
            "ante": ante,
            "quantita": qta,
            "posa": posa,
            **ris
        }

        # Generazione Testo Prospetto
        testo = (
            f"================================================\n"
            f"           PROSPETTO DI CALCOLO INFISSI         \n"
            f"================================================\n"
            f"Cliente:      {self.ultimo_calcolo['cliente']}\n"
            f"Data:         {datetime.now().strftime('%d/%m/%Y %H:%M')}\n"
            f"------------------------------------------------\n"
            f"SPECIFICHE TECNICHE SINGOLO SERRAMENTO:\n"
            f"• Dimensioni: {larg} mm (L) x {alt} mm (H)\n"
            f"• Superficie: {ris['area_reale_mq']} m² (Sviluppo profili: {ris['perimetro_m']} ml)\n"
            f"• Apertura:   {ante} Anta/e con ferramenta completa\n"
            f"• Profilo:    {profilo_scelto} (€ {costo_ml:.2f}/ml)\n"
            f"• Vetro:      {vetro_scelto} (€ {costo_mq:.2f}/m²)\n"
            f"• Posa:       {'Inclusa' if posa else 'Esclusa (Solo Fornitura)'}\n"
            f"------------------------------------------------\n"
            f"RIEPILOGO ECONOMICO:\n"
            f"• Prezzo Unitario Infisso:    € {ris['costo_unitario']:>10.2f}\n"
            f"• Quantità Richiesta:         x {qta:>10}\n"
            f"• Totale Imponibile:          € {ris['imponibile']:>10.2f}\n"
            f"• IVA (22%):                  € {ris['iva']:>10.2f}\n"
            f"================================================\n"
            f"TOTALE PREVENTIVO CHIAVI IN MANO: € {ris['totale_ivato']:>8.2f}\n"
            f"================================================\n"
        )

        self.txt_riepilogo.config(state="normal")
        self.txt_riepilogo.delete("1.0", tk.END)
        self.txt_riepilogo.insert(tk.END, testo)
        self.txt_riepilogo.config(state="disabled")

        self.btn_salva.config(state="normal")
        self.btn_esporta.config(state="normal")

    def salva_ordine_db(self):
        if not self.ent_cliente.get().strip():
            messagebox.showwarning("Campo Obbligatorio", "Inserire il nome del cliente prima di salvare in archivio.")
            self.ent_cliente.focus()
            return

        c = self.ultimo_calcolo
        dati = (
            self.ent_cliente.get().strip(),
            self.ent_telefono.get().strip(),
            datetime.now().strftime("%d/%m/%Y"),
            c["profilo"],
            c["vetro"],
            c["larghezza"],
            c["altezza"],
            c["ante"],
            c["quantita"],
            1 if c["posa"] else 0,
            c["totale_ivato"],
            "Preventivo"
        )
        id_creato = self.db.salva_preventivo(dati)
        self.aggiorna_tabella_ordini()
        messagebox.showinfo("Salvataggio Completato", f"Pratica #{id_creato} registrata con successo nell'archivio!")

    def esporta_preventivo_txt(self):
        if not self.ultimo_calcolo:
            return
        nome_file = f"Preventivo_{self.ultimo_calcolo['cliente'].replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        contenuto = self.txt_riepilogo.get("1.0", tk.END)
        with open(nome_file, "w", encoding="utf-8") as f:
            f.write(contenuto)
        messagebox.showinfo("Esportazione Riuscita",
                            f"Documento salvato nella cartella corrente:\n{os.path.abspath(nome_file)}")

    # --------------------------------------------------------------------------
    # TAB 2: ARCHIVIO ORDINI E AVANZAMENTO PRODUZIONE
    # --------------------------------------------------------------------------
    def costruisci_tab_ordini(self):
        frame_top = ttk.Frame(self.tab_ordini, padding=10)
        frame_top.pack(fill="both", expand=True)

        colonne = ("id", "data", "cliente", "telefono", "specifiche", "misure", "qta", "totale", "stato")
        self.tree = ttk.Treeview(frame_top, columns=colonne, show="headings", selectmode="browse")

        intestazioni = {
            "id": ("ID", 45),
            "data": ("Data", 85),
            "cliente": ("Cliente", 150),
            "telefono": ("Telefono", 100),
            "specifiche": ("Profilo & Vetro", 280),
            "misure": ("Dimensioni (AxL)", 120),
            "qta": ("Q.tà", 50),
            "totale": ("Totale IVA Inc.", 110),
            "stato": ("Stato Commessa", 120)
        }

        for col, (testo, larghezza) in intestazioni.items():
            self.tree.heading(col, text=testo)
            self.tree.column(col, width=larghezza, anchor="center" if col in ("id", "data", "qta", "stato") else "w")

        scrollbar = ttk.Scrollbar(frame_top, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscroll=scrollbar.set)
        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Barra Controlli Inferiore per Cambio Stato / Eliminazione
        frame_controlli = ttk.LabelFrame(self.tab_ordini, text=" Gestione Stato Commessa Selezionata ", padding=10)
        frame_controlli.pack(fill="x", padx=10, pady=(0, 10))

        ttk.Label(frame_controlli, text="Imposta Nuovo Stato:").pack(side="left", padx=5)
        self.cmb_nuovo_stato = ttk.Combobox(
            frame_controlli,
            values=["Preventivo", "Confermato - In Produzione", "Pronto in Magazzino", "Installato / Consegnato"],
            state="readonly", width=28
        )
        self.cmb_nuovo_stato.current(1)
        self.cmb_nuovo_stato.pack(side="left", padx=5)

        ttk.Button(
            frame_controlli, text="Aggiorna Stato", command=self.cambia_stato_selezionato
        ).pack(side="left", padx=10)

        ttk.Button(
            frame_controlli, text="Elimina Pratica", command=self.elimina_selezionato
        ).pack(side="right", padx=5)

        self.lbl_fatturato = ttk.Label(frame_controlli, text="Valore Totale Portafoglio: € 0.00",
                                       font=("Segoe UI", 10, "bold"))
        self.lbl_fatturato.pack(side="right", padx=25)

    def aggiorna_tabella_ordini(self):
        for item in self.tree.get_children():
            self.tree.delete(item)

        record = self.db.get_tutti_preventivi()
        somma_totale = 0.0

        for r in record:
            # r: id, cliente, telefono, data, profilo, vetro, larg, alt, ante, qta, posa, prezzo, stato
            specifiche = f"{r[4]} | {r[5]}"
            misure = f"{r[6]}x{r[7]} mm ({r[8]}A)"
            prezzo_fmt = f"€ {r[11]:,.2f}"
            somma_totale += r[11]

            self.tree.insert("", tk.END, values=(
                r[0], r[3], r[1], r[2], specifiche, misure, r[9], prezzo_fmt, r[12]
            ))

        self.lbl_fatturato.config(text=f"Valore Totale Portafoglio: € {somma_totale:,.2f}")

    def cambia_stato_selezionato(self):
        selezione = self.tree.selection()
        if not selezione:
            messagebox.showwarning("Nessuna Selezione", "Seleziona un ordine dalla tabella per aggiornarne lo stato.")
            return
        id_ordine = self.tree.item(selezione[0])["values"][0]
        nuovo_stato = self.cmb_nuovo_stato.get()
        self.db.aggiorna_stato_ordine(id_ordine, nuovo_stato)
        self.aggiorna_tabella_ordini()

    def elimina_selezionato(self):
        selezione = self.tree.selection()
        if not selezione:
            messagebox.showwarning("Nessuna Selezione", "Seleziona una pratica dalla tabella per eliminarla.")
            return
        id_ordine = self.tree.item(selezione[0])["values"][0]
        if messagebox.askyesno("Conferma Eliminazione",
                               f"Sei sicuro di voler eliminare definitivamente la pratica #{id_ordine}?"):
            self.db.elimina_preventivo(id_ordine)
            self.aggiorna_tabella_ordini()


# ==============================================================================
# 4. ENTRY POINT DELL'APPLICAZIONE
# ==============================================================================
if __name__ == "__main__":
    app = AppGestionaleInfissi()
    app.mainloop()