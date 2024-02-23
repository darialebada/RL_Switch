## Lebada Daria-Cristiana, 333CA
### Tema 1 RL - Implementare Switch

## Cerinta
Implementarea unui switch in Python (fisierul switch.py).

Testare:

Se va inițializa topologia virtuală și se va deschide câte un terminal pentru fiecare host,
câte un terminal pentru fiecare switch; terminalele pot fi identificate după titlu).

- sudo python3 checker/topo.py

Pornirea manuala a switch-urilor:
- make run_switch SWITCH_ID=X   // din terminalul unui switch, unde X este 0, 1 sau 2 si reprezinta ID-ul switch-ului.


## Tabela de Comutare
- Folosesc un HashMap in care voi asocia fiecarei adrese MAC un port (drumul catre acea adresa MAC).
- Daca am broadcast (adresa MAC destinatie este ff.ff.ff.ff.ff.ff), atunci trimit datele pe toate porturile,
mai putin catre cel de pe care am primit.
- Daca nu fac broadcast, verific daca am deja adresa MAC data in tabela CAM. Daca am gasit adresa, atunci stiu
pe ce port sa trimit (si trimit doar pe acela). Daca nu am intrarea respectiva in tabela, trimit catre toate
porturile, mai putin cel de pe care am primit pachetul.

## VLAN
- Am mai adaugat un HashMap in care retin tipul de vlan al fiecarei interfete (vlanul pentru legaturile de tip
access si "T" pentru legaturile de tip trunk).
- Prima data verific de pe ce legatura primesc pachetul: daca am legatura de tip access o sa iau vlan-ul din
dictionarul meu de vlan-uri, iar daca am legatura de tip trunk o sa elimin tag-ul 802.1q din pachetul primit.
- Cand trimit datele mai departe (am exact cazurile de la tabela CAM) verific mereu daca trimit pe o legatura
de tip trunk, caz in care trebuie sa adaug tag.

## STP
- Am adaugat inca un HashMap in care retin starile porturilor. Pentru simplitate, folosesc doar starile
"listening" si "blocking" (porturile root si designated sunt implicit in starea "listening").
- functia send_bdpu_every_second() va trimite cate un cadru de tip BPDU la fiecare secunda catre toate porturile
de tip trunk, doar daca switch-ul curent este root bridge. Cadrul va contine: MAC destinatie (cel de multicast
dat in cerinta), MAC sursa (adresa MAC a switch-ului), LLC_LENGTH (marimea pachetului), LLC_HEADER (DSAP, SSAP
si control), header BPDU (marimea BPDU Config) si BPDU config (am adaugat aici flags = 0, root bridge id, root
path cost, sender bridge id si port id).
- Daca primesc un cadru de tip BPDU (imi dau seama dupa adresa MAC destinatie), prima data extrag datele de
care am nevoie (root bridge id, sender path cost, sender bridge id).
- Verific daca e nevoie sa modific root bridge-ul (daca am gasit o prioritate mai mica), caz in care toate
porturile switch-ului curent vor trece din starea "blocking" in "listening", mai putin portul care face legatura
cu noul root bridge.
- Daca am gasit aceeasi valoare de root bridge, caut un drum mai putin costisitor catre acesta si modific starile
porturilor dupa caz.
- La final am grija ca toate porturile trunk ale root bridge-ului sa fie in starea "listening".
- De fiecare data cand trimit un pachet pe o legatura de tip trunk ma asigur ca acel port este in starea "listening".
