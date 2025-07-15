# Faza 6 / Zadanie 3: Rozbudowa automatyzacji z monitoringiem

## Cel zadania
Rozszerzyć zestaw automatyzacji do 20+ reguł z pełnym monitoringiem, walidacją i niskim poziomem false positives (<1%).

## Blok 0: Prerequisites check

#### Zadania atomowe:
1. **[ ] Current automation inventory**
   - **Metryka**: List existing automations
   - **Walidacja**: 
     ```bash
     python list_automations.py --active
     # Shows <10 basic automations
     cat automations/*.yaml | grep -c "^name:"
     ```
   - **Czas**: 0.5h

2. **[ ] False positive baseline**
   - **Metryka**: Current false positive rate
   - **Walidacja**: 
     ```python
     stats = get_automation_statistics(days=7)
     print(f"Current false positive rate: {stats.false_positive_rate}%")
     assert stats.false_positive_rate < 5  # Need improvement
     ```
   - **Czas**: 0.5h

## Dekompozycja na bloki zadań

### Blok 1: Advanced automation rules

#### Zadania atomowe:
1. **[ ] Context-aware automations**
   - **Metryka**: Time/presence based rules
   - **Walidacja**: 
     ```yaml
     # Example automation
     - name: "Morning routine"
       triggers:
         - platform: time
           at: "07:00"
         - platform: motion
           entity: sensor.bedroom_motion
       conditions:
         - condition: time
           after: "06:30"
           before: "08:00"
         - condition: state
           entity: person.owner
           state: home
     ```
   - **Czas**: 2.5h

2. **[ ] Multi-trigger combinations**
   - **Metryka**: Complex trigger logic
   - **Walidacja**: 
     ```python
     automation = get_automation("presence_and_gesture")
     assert len(automation.triggers) >= 2
     assert automation.mode == "single"  # Prevent multiple runs
     assert automation.has_cooldown == True
     ```
   - **Czas**: 2h

3. **[ ] Smart scene detection**
   - **Metryka**: Recognize activity patterns
   - **Walidacja**: 
     ```python
     scenes = ["cooking", "movie_night", "party", "sleeping"]
     for scene in scenes:
         automation = get_scene_automation(scene)
         assert automation.confidence_threshold > 0.8
         assert len(automation.required_detections) > 2
     ```
   - **Czas**: 3h

#### Metryki sukcesu bloku:
- 20+ automations defined
- Complex logic supported
- Scenes recognized

### Blok 2: False positive reduction

#### Zadania atomowe:
1. **[ ] Confidence thresholds tuning**
   - **Metryka**: Optimal thresholds per automation
   - **Walidacja**: 
     ```python
     thresholds = optimize_confidence_thresholds()
     for automation, threshold in thresholds.items():
         assert 0.7 <= threshold <= 0.95
         # Validate reduces false positives
         assert test_with_threshold(automation, threshold).fp_rate < 0.01
     ```
   - **Czas**: 2h

2. **[ ] Debouncing and cooldowns**
   - **Metryka**: Prevent rapid triggers
   - **Walidacja**: 
     ```python
     config = get_debounce_config()
     assert config.motion_cooldown >= 30  # seconds
     assert config.gesture_debounce >= 2   # seconds
     assert config.voice_command_timeout >= 5
     ```
   - **Czas**: 1.5h

3. **[ ] Validation rules**
   - **Metryka**: Secondary confirmation
   - **Walidacja**: 
     ```yaml
     validation:
       person_at_door:
         requires:
           - face_detected: true
           - motion_detected: true
           - confidence: ">0.85"
         within_seconds: 5
     ```
   - **Czas**: 2h

#### Metryki sukcesu bloku:
- False positives <1%
- Validations working
- No automation storms

### Blok 3: Monitoring and management

#### Zadania atomowe:
1. **[ ] Automation health dashboard**
   - **Metryka**: Status of all automations
   - **Walidacja**: 
     ```promql
     # Automation health score
     (sum(automation_success_total) / 
      sum(automation_triggered_total)) * 100
     # Should be >98%
     ```
   - **Czas**: 1.5h

2. **[ ] A/B testing framework**
   - **Metryka**: Test automation variants
   - **Walidacja**: 
     ```python
     test = create_ab_test(
         automation="morning_routine",
         variant_a={"threshold": 0.8},
         variant_b={"threshold": 0.9}
     )
     assert test.split_ratio == 0.5
     assert test.min_sample_size >= 100
     ```
   - **Czas**: 2h

#### Metryki sukcesu bloku:
- All automations monitored
- A/B testing possible
- Easy management

## Całościowe metryki sukcesu zadania

1. **Quantity**: 20+ production automations
2. **Quality**: <1% false positive rate
3. **Coverage**: 90% of use cases automated

## Deliverables

1. `/automations/` - 20+ automation definitions
2. `/src/automation_engine/` - Enhanced engine
3. `/config/automation_rules.yaml` - Rule configurations
4. `/dashboards/automation-health.json` - Health dashboard
5. `/docs/automation-cookbook.md` - Examples and patterns

## Narzędzia

- **PyYAML**: Automation definitions
- **scikit-learn**: Threshold optimization
- **APScheduler**: Time-based triggers
- **Redis**: State management

## Zależności

- **Wymaga**: 
  - Detection services stable
  - HA integration working
- **Blokuje**: Production deployment

## Ryzyka i mitigacje

| Ryzyko | Prawdopodobieństwo | Wpływ | Mitigacja | Early Warning |
|--------|-------------------|-------|-----------|---------------|
| Automation conflicts | Średnie | Średni | Priority system, mutex locks | Multiple triggers same entity |
| Complexity explosion | Wysokie | Średni | Rule templates, inheritance | >50 lines per automation |

## Rollback Plan

1. **Detekcja problemu**: 
   - False positives >5%
   - Automation loops
   - User complaints

2. **Kroki rollback**:
   - [ ] Disable new automations
   - [ ] Restore previous rule set
   - [ ] Clear automation state
   - [ ] Review logs for issues

3. **Czas rollback**: <10 min

## Następne kroki

Po ukończeniu tego zadania, przejdź do:
→ [04-management-ui.md](./04-management-ui.md)