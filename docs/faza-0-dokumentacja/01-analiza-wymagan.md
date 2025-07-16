# Faza 0 / Zadanie 1: Analiza i dokumentacja wymagań

## Cel zadania

Przeprowadzenie kompletnej analizy wymagań systemowych i utworzenie pełnej dokumentacji wymagań funkcjonalnych i niefunkcjonalnych dla systemu detekcji i automatyzacji wizyjnej.

## Dekompozycja na bloki zadań

### Blok 1: Analiza wymagań funkcjonalnych (RF)

#### Zadania atomowe

1. **[x] Identyfikacja głównych aktorów systemu**
   - **Metryka**: Min. 3 aktorów (User, System, Home Assistant)
   - **Walidacja**: `cat docs/requirements/actors.md | grep "^##" | wc -l`
   - **Czas**: 2h

2. **[x] Mapowanie use cases dla każdego aktora**
   - **Metryka**: Min. 15 use cases
   - **Walidacja**: Diagram UML z use cases w PlantUML
   - **Czas**: 4h

3. **[x] Utworzenie wymagań funkcjonalnych z priorytetami**
   - **Metryka**: 20+ wymagań w formacie RF001-RF020+
   - **Walidacja**:

     ```bash
     grep -E "^- \*\*RF[0-9]{3}\*\*:" functional-requirements.md | wc -l
     # Expected: ≥20
     ```

   - **Czas**: 6h

4. **[x] Kategoryzacja wymagań (MoSCoW)**
   - **Metryka**: 100% wymagań z przypisanym priorytetem
   - **Walidacja**: Każde RF ma tag: [MUST]/[SHOULD]/[COULD]/[WONT]
   - **Czas**: 2h

#### Metryki sukcesu bloku

- Wszystkie główne funkcjonalności pokryte
- Format zgodny z IEEE 830
- Peer review przeszedł bez major issues

### Blok 2: Analiza wymagań niefunkcjonalnych (RNF)

#### Zadania atomowe

1. **[x] Wymagania wydajnościowe (Performance)**
   - **Metryka**: Min. 5 mierzalnych KPI
   - **Walidacja**: Każde ma target value (np. latency <2s)
   - **Czas**: 3h

2. **[x] Wymagania bezpieczeństwa (Security)**
   - **Metryka**: Pokrycie OWASP Top 10 dla IoT
   - **Walidacja**: Security checklist 100% wypełniona
   - **Czas**: 3h

3. **[x] Wymagania niezawodnościowe (Reliability)**
   - **Metryka**: SLA zdefiniowane (uptime, MTBF, MTTR)
   - **Walidacja**: `grep -E "(99\.[0-9]%|MTBF|MTTR)" non-functional-requirements.md`
   - **Czas**: 2h

4. **[x] Wymagania skalowalności i utrzymania**
   - **Metryka**: Zdefiniowane limity (cameras, FPS, storage)
   - **Walidacja**: Capacity planning sheet wypełniony
   - **Czas**: 2h

#### Metryki sukcesu bloku

- Wszystkie kategorie ISO 25010 pokryte
- 100% wymagań ma metryki
- Testowalne acceptance criteria

### Blok 3: Utworzenie macierzy śledzenia wymagań

#### Zadania atomowe

1. **[x] Przygotowanie szablonu macierzy**
   - **Metryka**: Kolumny: ID, Nazwa, Komponent, Test, Status
   - **Walidacja**: CSV/Excel z nagłówkami
   - **Czas**: 1h

2. **[x] Mapowanie wymagań do komponentów**
   - **Metryka**: 100% RF/RNF zmapowanych
   - **Walidacja**:

     ```python
     import pandas as pd
     df = pd.read_csv('requirements_matrix.csv')
     assert df['Component'].notna().all()
     ```

   - **Czas**: 3h

3. **[x] Linking wymagań do test cases (placeholder)**
   - **Metryka**: Każde wymaganie ma test ID
   - **Walidacja**: Kolumna 'Test_ID' wypełniona
   - **Czas**: 2h

#### Metryki sukcesu bloku

- Pełna traceability od wymagania do implementacji
- Export do JIRA/podobnego możliwy
- Automated validation passing

### Blok 4: Walidacja i akceptacja wymagań

#### Zadania atomowe

1. **[x] Internal review dokumentacji**
   - **Metryka**: 0 krytycznych uwag
   - **Walidacja**: Review checklist completed
   - **Czas**: 2h

2. **[x] Sesja z "stakeholders" (sam ze sobą jako hobbysta)**
   - **Metryka**: Wszystkie niejasności wyjaśnione
   - **Walidacja**: Meeting notes z decyzjami
   - **Czas**: 1h

3. **[x] Finalizacja i wersjonowanie**
   - **Metryka**: v1.0 tagged w git
   - **Walidacja**: `git tag | grep "requirements-v1.0"`
   - **Czas**: 1h

#### Metryki sukcesu bloku

- Sign-off na wymagania
- Baseline utworzony
- Change control process defined

## Całościowe metryki sukcesu zadania

1. **Kompletność**: 100% obszarów systemu pokrytych wymaganiami
2. **Jakość**: 0 wymagań niejednoznacznych (ambiguous)
3. **Mierzalność**: 100% wymagań ma acceptance criteria
4. **Czas**: Ukończone w 24h roboczych (3 dni)

## Deliverables

1. `/docs/requirements/functional-requirements.md`
2. `/docs/requirements/non-functional-requirements.md`
3. `/docs/requirements/use-cases.md`
4. `/docs/requirements/requirements-matrix.csv`
5. `/docs/requirements/actors.md`

## Narzędzia

- **PlantUML**: Diagramy use case
- **Markdown + Vale**: Dokumentacja z lintingiem
- **Git**: Wersjonowanie
- **Python/Pandas**: Walidacja macierzy

## Następne kroki

Po ukończeniu tego zadania, przejdź do:
→ [02-struktura-projektu.md](./02-struktura-projektu.md)
