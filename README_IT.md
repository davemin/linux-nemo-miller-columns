# Nemo Miller Columns

Un'estensione per Nemo (file manager di Linux Mint/Cinnamon) che permette di visualizzare i file in stile **Miller Columns**, simile al Finder di macOS.

[Miller Columns](https://en.wikipedia.org/wiki/Miller_columns)

*[Read in English](README.md)*

## Caratteristiche

- **Vista Miller Columns**: Naviga le cartelle in colonne affiancate
- **Colonne ridimensionabili**: Trascina i separatori per regolare la larghezza delle colonne
- **Distribuzione equa**: Le colonne si distribuiscono automaticamente in modo equo (es. 4 colonne = 25% ciascuna)
- **Ricerca file**: Cerca per nome file E contenuto, ricorsivamente nelle sottocartelle
- **Pannello di anteprima**: Mostra informazioni e anteprima del file selezionato
- **Integrazione con Nemo**: Click destro → "Apri in Miller Columns"
- **Navigazione rapida**: Barra del percorso cliccabile, pulsanti home e indietro
- **Anteprima immagini**: Visualizza miniature delle immagini
- **Apri in terminale**: Pulsante per aprire un terminale nella cartella corrente
- **Scorciatoie da tastiera**: Ctrl+F per cercare, Backspace per tornare indietro, Esc per chiudere

## Requisiti

- Linux Mint 22 (o altra distribuzione con Nemo)
- Nemo 6.x
- Python 3
- GTK 3
- nemo-python (per l'estensione)

## Installazione

### Automatica (consigliata)

```bash
cd /percorso/di/nemo-miller-columns
./install.sh
```

Lo script installerà automaticamente le dipendenze mancanti.

### Manuale

1. **Installa le dipendenze**:

```bash
sudo apt update
sudo apt install python3 python3-gi gir1.2-gtk-3.0 nemo-python
```

2. **Crea le directory**:

```bash
mkdir -p ~/.local/share/nemo-miller-columns
mkdir -p ~/.local/share/nemo-python/extensions
```

3. **Copia i file**:

```bash
# Applicazione principale
cp nemo_miller_columns.py ~/.local/share/nemo-miller-columns/
chmod +x ~/.local/share/nemo-miller-columns/nemo_miller_columns.py

# Estensione Nemo
cp nemo-miller-columns-extension.py ~/.local/share/nemo-python/extensions/
```

4. **Riavvia Nemo**:

```bash
nemo -q
```

## Utilizzo

### Da Nemo (menu contestuale)

1. Apri Nemo e naviga in una cartella
2. Click destro su una cartella **oppure** sullo sfondo vuoto
3. Seleziona **"Apri in Miller Columns"**

### Da terminale

```bash
python3 ~/.local/share/nemo-miller-columns/nemo_miller_columns.py [percorso]
```

Esempi:
```bash
# Apri la home
python3 ~/.local/share/nemo-miller-columns/nemo_miller_columns.py

# Apri una cartella specifica
python3 ~/.local/share/nemo-miller-columns/nemo_miller_columns.py /home/utente/Documenti
```

## Scorciatoie da tastiera

| Tasto | Azione |
|-------|--------|
| `Ctrl+F` | Focus sulla barra di ricerca |
| `Esc` | Esci dalla ricerca / Chiudi applicazione |
| `Backspace` | Vai alla cartella padre |
| `Enter` / Doppio click su file | Apri con applicazione predefinita |
| `Enter` / Click su cartella | Naviga nella cartella |

## Ricerca

La barra di ricerca permette di trovare file per nome o contenuto:

- **Ricerca live**: I risultati appaiono mentre digiti (con debounce di 300ms)
- **Ricorsiva**: Cerca in tutte le sottocartelle dalla posizione corrente
- **Ricerca contenuto**: Cerca anche dentro i file di testo (salta file > 10MB)
- **Indicatore match**: Mostra badge "in content" per i match nel contenuto
- Clicca su un risultato per navigare e aprire il file

## Ridimensionamento Colonne

- **Distribuzione automatica**: Le colonne si distribuiscono automaticamente in modo equo
- **Ridimensionamento manuale**: Trascina i separatori verticali tra le colonne per regolare le larghezze
- **Larghezza minima**: Ogni colonna ha una larghezza minima di 100px
- **Feedback visivo**: Il cursore cambia quando passi sopra i separatori

## Struttura del progetto

```
nemo-miller-columns/
├── nemo_miller_columns.py           # Applicazione principale GTK
├── nemo-miller-columns-extension.py # Estensione per menu Nemo
├── install.sh                       # Script di installazione
├── uninstall.sh                     # Script di disinstallazione
├── README.md                        # Documentazione in inglese
└── README_IT.md                     # Documentazione in italiano
```

## Disinstallazione

```bash
cd /percorso/di/nemo-miller-columns
./uninstall.sh
```

## Risoluzione problemi

### L'opzione non appare nel menu contestuale

1. Assicurati che `nemo-python` sia installato:
   ```bash
   sudo apt install nemo-python
   ```

2. Verifica che l'estensione sia nella cartella corretta:
   ```bash
   ls ~/.local/share/nemo-python/extensions/
   ```

3. Riavvia Nemo completamente:
   ```bash
   nemo -q
   nemo &
   ```

4. Se ancora non funziona, prova a riavviare il sistema.

### Errore "Nemo module not found"

Il modulo `gi.repository.Nemo` è disponibile solo all'interno di Nemo. L'estensione funzionerà correttamente quando caricata da Nemo stesso.

### L'applicazione non si avvia

Verifica che GTK 3 sia installato correttamente:
```bash
python3 -c "import gi; gi.require_version('Gtk', '3.0'); from gi.repository import Gtk; print('OK')"
```

## Licenza

MIT License - Sei libero di usare, modificare e distribuire questo software.

## Contributi

Contributi, bug reports e feature requests sono benvenuti!
