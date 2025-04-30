# PoplavniAlarm

Spletna aplikacija je namenjena pravočasnemu opozarjanju oseb zaradi višine reke Savinje za mesto Laško.

To doseže tako, da vsako uro preglejuje https://www.arso.gov.si/vode/podatki/stanje_voda_samodejne.html in to tabelo posodablja vsako uro.

Potem si določimo prag pri katerem naj javlja in za vsakega uporabnika nato razpošilja E-Maile, ko voda doseže svoj prag.

Aplikacija je samostojna in deluje na lokalnem strežniku.




### Namestitev (lokalno)

1. **Kloniraj repozitorij**:
```bash
git clone https://github.com/JernejRozman/PoplavniAlarm
```
3. **Namestimo odvisnosti:**

```bash
pip install -r requirements.txt
```

3. **Poženemo flask strežnik:**

```bash
flask --app flaskr run --debug
```

