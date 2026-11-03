# InfissiPro ERP - Sistema Gestionale Serramenti

## Indice
1. [Panoramica del Progetto](#panoramica-del-progetto)
2. [Architettura del Software](#architettura-del-software)
3. [Requisiti di Sistema](#requisiti-di-Sistema)
4. [Struttura del Database](#struttura-del-database)
5. [Installazione e Configurazione](#installazione-e-configurazione)
6. [Guida all'Uso](#guida-alluso)

---

## Panoramica del Progetto
InfissiPro ERP è un sistema gestionale desktop sviluppato in Python, progettato specificamente per le aziende produttrici e rivenditrici di infissi e serramenti. L'applicazione integra un motore di calcolo ingegneristico-commerciale per la stima dei preventivi, un database relazionale SQLite per la persistenza dei dati e un'interfaccia grafica intuitiva basata su librerie standard.

---

## Architettura del Software
L'applicazione è strutturata in tre livelli principali, garantendo una netta separazione delle responsabilità:

1. **Livello Database (SQLite3):** Gestisce la connessione, la creazione automatica delle tabelle e la persistenza dei dati relativi al listino materiali (profili e vetri) e allo storico dei preventivi/ordini.
2. **Motore di Calcolo Ingegneristico e Commerciale (`CalcolatoreInfissi`):** Esegue la logica di calcolo geometrico ed economico. Elabora il perimetro dei profili (inclusi i montanti per ante multiple), calcola la superficie del vetro applicando i criteri di minimo fatturabile, aggiunge i costi di ferramenta e posa in opera, e calcola l'imponibile, l'IVA e il totale ivato.
3. **Interfaccia Grafica (`AppGestionaleInfissi`):** Sviluppata con Tkinter e il modulo ttk, offre un layout a schede per facilitare la navigazione tra il configuratore di nuovi preventivi e l'archivio delle commesse.

---

## Requisiti di Sistema
- **Linguaggio:** Python 3.8 o superiore.
- **Librerie Native:** 
  - `sqlite3`
  - `tkinter`
  - `datetime`
  - `os`
- Non sono richieste dipendenze esterne o pacchetti di terze parti installabili tramite pip.

---

## Struttura del Database
Il database locale (`azienda_infissi.db`) viene generato automaticamente al primo avvio e si compone di due tabelle principali:

- **`listino`:**
  - `id`: Chiave primaria autoincrementale.
  - `categoria`: Tipologia di voce ('Profilo' o 'Vetro').
  - `nome`: Descrizione del materiale (univoca).
  - `prezzo_base`: Costo unitario (al metro lineare per i profili, al metro quadro per i vetri).

- **`preventivi`:**
  - `id`: Identificativo univoco della pratica.
  - `cliente`: Nome o ragione sociale del committente.
  - `telefono`: Contatto telefonico.
  - `data_creazione`: Data di emissione del documento.
  - `profilo`: Materiale del profilo selezionato.
  - `vetro`: Tipologia di vetrocamera selezionata.
  - `larghezza_mm`: Larghezza del serramento in millimetri.
  - `altezza_mm`: Altezza del serramento in millimetri.
  - `ante`: Numero di ante del serramento.
  - `quantita`: Numero di elementi identici richiesti.
  - `posa_inclusa`: Indicatore booleano (1/0) relativo al servizio di montaggio.
  - `prezzo_totale`: Valore complessivo ivato.
  - `stato`: Stato corrente della commessa (es. Preventivo, In Produzione, Consegnato).

---

## Installazione e Configurazione

1. Clonare o scaricare il codice sorgente del progetto nella directory di lavoro locale.
2. Assicurarsi di disporre di un ambiente Python 3.x correttamente configurato sul proprio sistema operativo.
3. Posizionarsi tramite terminale nella cartella contenente lo script principale.
4. Avviare l'applicazione eseguendo il comando:
   ```bash
   python nome_file.py
   ```
   *(Sostituire `nome_file.py` con il nome effettivo dello script Python)*

---

## Guida all'Uso

### Scheda 1: Nuovo Preventivo / Commessa
- Inserire i dati anagrafici del cliente negli appositi campi di testo.
- Selezionare il materiale del profilo e la tipologia di vetrocamera dai menu a tendina precaricati dal listino.
- Impostare le dimensioni geometriche (larghezza e altezza in millimetri), il numero di ante e la quantità di infissi identici.
- Specificare l'inclusione o l'esclusione della posa in opera qualificata.
- Cliccare sul pulsante **CALCOLA PREVENTIVO** per visualizzare il prospetto tecnico-economico dettagliato.
- Utilizzare i pulsanti dedicati per salvare la pratica nell'archivio ordini o per esportare il preventivo in formato di testo (`.txt`).

### Scheda 2: Archivio Preventivi & Produzione
- Visualizzare l'elenco completo delle pratiche registrate all'interno della tabella riassuntiva.
- Selezionare una commessa specifica per aggiornare il suo stato di avanzamento produttivo tramite il menu a tendina inferiore.
- Monitorare il valore economico complessivo del portafoglio ordini tramite l'indicatore finanziario a fondo pagina.
- Rimuovere eventuali pratiche obsolete tramite la funzione di eliminazione.
