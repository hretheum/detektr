# Szablon Dekompozycji Zadania z Promptami dla LLM

```markdown
# Faza X / Zadanie Y: [Nazwa zadania]

<!-- 
LLM PROMPT dla całego zadania:
Analizując to zadanie, upewnij się że:
1. Cel jest jasny i biznesowo uzasadniony
2. Dekompozycja pokrywa 100% zakresu zadania
3. Nie ma luk między blokami zadań
4. Całość można ukończyć w podanym czasie
-->

## Cel zadania
[1-2 zdania opisujące co chcemy osiągnąć i dlaczego to ważne dla projektu]

## Blok 0: Prerequisites check
<!-- 
LLM PROMPT: Ten blok jest OBOWIĄZKOWY dla każdego zadania.
Sprawdź czy wszystkie zależności są spełnione ZANIM rozpoczniesz główne zadanie.
-->

#### Zadania atomowe:
1. **[ ] Weryfikacja zależności systemowych**
   - **Metryka**: Wszystkie wymagane komponenty dostępne
   - **Walidacja**: `./scripts/check-prerequisites.sh` returns 0
   - **Czas**: 0.5h

2. **[ ] Backup obecnego stanu (jeśli dotyczy)**
   - **Metryka**: Backup kompletny, restore przetestowany
   - **Walidacja**: `ls -la /backups/$(date +%Y%m%d)/` pokazuje pliki
   - **Czas**: 0.5h

## Dekompozycja na bloki zadań

### Blok 1: [Nazwa logicznej grupy zadań]
<!-- 
LLM PROMPT dla bloku:
Dekomponując ten blok:
1. Każde zadanie atomowe musi być wykonalne w MAX 3h
2. Zadania w bloku powinny być logicznie powiązane
3. Kolejność zadań musi mieć sens (dependencies)
4. Blok powinien dostarczać konkretną wartość biznesową
-->

#### Zadania atomowe:
1. **[ ] [Nazwa zadania atomowego]**
   <!-- 
   LLM PROMPT dla zadania atomowego:
   To zadanie musi:
   - Mieć JEDEN konkretny deliverable
   - Być wykonalne przez jedną osobę bez przerw
   - Mieć jasne kryterium "done"
   - NIE wymagać czekania na zewnętrzne zależności
   -->
   - **Metryka**: [Konkretna liczba/procent/stan - np. "Response time <100ms w 95% przypadków"]
   - **Walidacja**: 
     ```bash
     # LLM PROMPT: Podaj DOKŁADNĄ komendę lub skrypt
     # który JEDNOZNACZNIE potwierdzi osiągnięcie metryki
     [komenda która zwraca measureable output]
     ```
   - **Czas**: [MAX 3h, realistically estimated]

2. **[ ] [Nazwa zadania atomowego]**
   - **Metryka**: 
   - **Walidacja**: 
   - **Czas**: 

#### Metryki sukcesu bloku:
<!-- 
LLM PROMPT dla metryk bloku:
Metryki muszą potwierdzać że blok osiągnął swój cel.
Powinny być:
1. Mierzalne automatycznie gdzie możliwe
2. Agregować metryki zadań atomowych
3. Dawać pewność że można przejść do następnego bloku
-->
- [Kryterium 1 - wymiernie]
- [Kryterium 2 - wymiernie]
- [Kryterium 3 - wymiernie]

### Blok 2: [Nazwa kolejnej grupy]

#### Zadania atomowe:
[...]

#### Metryki sukcesu bloku:
[...]

## Całościowe metryki sukcesu zadania
<!-- 
LLM PROMPT dla metryk całościowych:
Te metryki muszą:
1. Potwierdzać osiągnięcie celu biznesowego zadania
2. Być weryfikowalne przez stakeholdera (self w tym przypadku)
3. Agregować najważniejsze metryki z bloków
4. Być SMART (Specific, Measurable, Achievable, Relevant, Time-bound)
-->

1. **[Kategoria]**: [Opis metryki z wartością docelową]
2. **[Kategoria]**: [Opis metryki z wartością docelową]
3. **[Kategoria]**: [Opis metryki z wartością docelową]

## Deliverables
<!-- 
LLM PROMPT: Lista WSZYSTKICH artefaktów które powstaną.
Każdy deliverable musi:
1. Mieć konkretną ścieżkę w filesystem
2. Być wymieniony w jakimś zadaniu atomowym
3. Mieć jasny format i przeznaczenie
-->

1. [Ścieżka do pliku/artefaktu 1]
2. [Ścieżka do pliku/artefaktu 2]
3. [...]

## Narzędzia
<!-- 
LLM PROMPT: Wymień TYLKO narzędzia faktycznie używane w zadaniach.
Dla każdego podaj:
1. Dokładną nazwę i wersję (jeśli istotna)
2. Konkretne zastosowanie w tym zadaniu
3. Alternatywy jeśli główne narzędzie zawiedzie
-->

- **[Narzędzie 1]**: [Do czego używane]
- **[Narzędzie 2]**: [Do czego używane]

## Zależności

- **Wymaga**: [Zadania które muszą być ukończone przed tym]
- **Blokuje**: [Zadania które czekają na to zadanie]

## Ryzyka i mitigacje
<!-- 
LLM PROMPT dla ryzyk:
Identyfikuj REALNE ryzyka które mogą wystąpić podczas realizacji.
Dla każdego ryzyka:
1. Opisz konkretny scenariusz
2. Oceń realistycznie prawdopodobieństwo
3. Zaproponuj WYKONALNĄ mitigację
4. Dodaj trigger/early warning sign
-->

| Ryzyko | Prawdopodobieństwo | Wpływ | Mitigacja | Early Warning |
|--------|-------------------|-------|-----------|---------------|
| [Opis] | Niskie/Średnie/Wysokie | Niski/Średni/Wysoki | [Jak zapobiec] | [Jak wcześnie wykryć] |

## Rollback Plan
<!-- 
LLM PROMPT: KAŻDE zadanie musi mieć plan cofnięcia zmian.
Opisz:
1. Jak wykryć że coś poszło źle
2. Kroki do przywrócenia poprzedniego stanu
3. Maksymalny czas rollbacku
-->

1. **Detekcja problemu**: [Jak poznać że należy cofnąć]
2. **Kroki rollback**:
   - [ ] Krok 1
   - [ ] Krok 2
3. **Czas rollback**: [np. <15 min]

## Następne kroki

Po ukończeniu tego zadania, przejdź do:
→ [XX-nazwa-nastepnego.md](./XX-nazwa-nastepnego.md)
```

## Instrukcje dla LLM przy wypełnianiu szablonu

### KRYTYCZNE ZASADY:

1. **Reguła 3h**: ŻADNE zadanie atomowe nie może trwać >3h
2. **Reguła jednego outcome**: Zadanie atomowe = jeden deliverable
3. **Reguła mierzalności**: Każda metryka musi mieć komendę do weryfikacji
4. **Reguła kompletności**: Suma zadań atomowych = 100% zakresu bloku
5. **Reguła wykonalności**: Zadanie może wykonać jedna osoba bez przerw

### Struktura dekompozycji:

```
Zadanie główne (dni/tygodnie)
└── Blok 0: Prerequisites (0.5-1h)
└── Blok zadań (4-8h)
    └── Zadanie atomowe (1-3h)
        └── Konkretna czynność
        └── Mierzalna metryka  
        └── Automatyczna walidacja
```

### Przykłady dobrych zadań atomowych:

✅ DOBRE:
- "Utworzenie klasy DatabaseConnection z connection pooling"
- "Napisanie unit testów dla modułu authentication (80% coverage)"
- "Konfiguracja nginx reverse proxy dla /api/* endpoints"

❌ ZŁE:
- "Implementacja backendu" (za ogólne)
- "Testowanie systemu" (za szerokie)  
- "Optymalizacja wydajności" (niemierzalne)

### Szacowanie czasu:

1. Oszacuj optymistycznie
2. Dodaj 50% na debugging  
3. Dodaj 20% na dokumentację
4. Zaokrąglij w górę do 0.5h
5. Jeśli >3h, podziel zadanie

### Tworzenie metryk:

Dobra metryka odpowiada na pytania:
- Co dokładnie mierzymy? (np. "response time")
- Jaka jest wartość docelowa? (np. "<100ms")
- W jakich warunkach? (np. "dla 95% requestów")
- Jak zmierzymy? (np. "k6 load test wynik")

### Prompty do copy-paste:

Gdy tworzysz blok zadań, użyj:
```
Zdekomponuj [nazwa bloku] na zadania atomowe (max 3h każde), 
gdzie każde zadanie ma jeden mierzalny output i może być 
wykonane bez przerw przez jedną osobę.
```

Gdy tworzysz metrykę, użyj:
```
Stwórz mierzalną metrykę dla [zadanie], która ma:
- konkretną wartość docelową z jednostką
- automatyczny sposób weryfikacji (komenda/skrypt)
- jasne kryterium sukces/porażka
```