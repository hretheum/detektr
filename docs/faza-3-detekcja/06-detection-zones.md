# Faza 3 / Zadanie 6: Detection Zones Configuration

## Cel zadania

Implementacja systemu definiowania stref detekcji dla każdej kamery, umożliwiając selektywne przetwarzanie tylko wybranych obszarów obrazu.

## Dekompozycja na bloki zadań

### Blok 0: Prerequisites

#### Zadania atomowe

1. **[ ] Analiza wymagań dla zone management**
   - **Metryka**: Use cases documented
   - **Walidacja**: Requirements complete
   - **Czas**: 1h

2. **[ ] UI/UX design dla zone editor**
   - **Metryka**: Mockups created
   - **Walidacja**: Design review done
   - **Czas**: 2h

### Blok 1: Zone definition system

#### Zadania atomowe

1. **[ ] TDD: Zone model i validation**
   - **Metryka**: Polygon, rectangle, circle zones
   - **Walidacja**: `pytest tests/test_zone_models.py`
   - **Czas**: 2h

2. **[ ] Zone persistence layer**
   - **Metryka**: CRUD operations for zones
   - **Walidacja**: Database integration test
   - **Czas**: 2h

3. **[ ] Multi-camera zone management**
   - **Metryka**: Zones per camera config
   - **Walidacja**: Multi-cam zone test
   - **Czas**: 2h

### Blok 2: Zone editor implementation

#### Zadania atomowe

1. **[ ] Web-based zone editor UI**
   - **Metryka**: Draw zones on camera view
   - **Walidacja**: UI interaction test
   - **Czas**: 3h

2. **[ ] Real-time zone preview**
   - **Metryka**: Live zone overlay
   - **Walidacja**: Preview accuracy
   - **Czas**: 2h

3. **[ ] Zone templates i presets**
   - **Metryka**: Common zone patterns
   - **Walidacja**: Template application
   - **Czas**: 2h

### Blok 3: Zone processing integration

#### Zadania atomowe

1. **[ ] Zone mask generation**
   - **Metryka**: Binary masks for detection
   - **Walidacja**: Mask accuracy test
   - **Czas**: 2h

2. **[ ] Detection filtering by zone**
   - **Metryka**: Only in-zone detections
   - **Walidacja**: Filtering accuracy
   - **Czas**: 2h

3. **[ ] Performance optimization**
   - **Metryka**: <5ms zone check overhead
   - **Walidacja**: Performance benchmark
   - **Czas**: 3h

### Blok 4: Advanced zone features

#### Zadania atomowe

1. **[ ] Time-based zone activation**
   - **Metryka**: Schedule zone on/off
   - **Walidacja**: Schedule test
   - **Czas**: 2h

2. **[ ] Zone-specific detection params**
   - **Metryka**: Different thresholds per zone
   - **Walidacja**: Parameter override test
   - **Czas**: 2h

3. **[ ] Zone analytics i heatmaps**
   - **Metryka**: Activity visualization
   - **Walidacja**: Heatmap generation
   - **Czas**: 2h

## Całościowe metryki sukcesu zadania

1. **Usability**: Zone setup <2 min per camera
2. **Performance**: <5% CPU overhead
3. **Accuracy**: Pixel-perfect zone boundaries
4. **Flexibility**: Complex zone shapes supported

## Deliverables

1. `services/zone-manager/` - Zone service
2. `web/zone-editor/` - Web UI
3. `src/domain/zones/` - Zone models
4. `scripts/zone-migration/` - Migration tools
5. `docs/zone-configuration.md` - User guide

## Narzędzia

- **FastAPI**: Zone API
- **React/Vue**: Zone editor UI
- **Shapely**: Geometry operations
- **OpenCV**: Mask generation
- **PostgreSQL+PostGIS**: Spatial data

## Blok 5: DEPLOYMENT NA SERWERZE NEBULA

### 🎯 **NOWA PROCEDURA - UŻYJ UNIFIED DOCUMENTATION**

**Wszystkie procedury deploymentu** znajdują się w: `docs/deployment/services/zone-manager.md`

### Zadania atomowe

1. **[ ] Deploy via CI/CD pipeline**
   - **Metryka**: Automated deployment to Nebula via GitHub Actions
   - **Walidacja**: `git push origin main` triggers deployment
   - **Procedura**: [docs/deployment/services/zone-manager.md#deploy](docs/deployment/services/zone-manager.md#deploy)

2. **[ ] Konfiguracja PostGIS na Nebuli**
   - **Metryka**: PostgreSQL with PostGIS extension
   - **Walidacja**: `SELECT PostGIS_Version()`
   - **Procedura**: [docs/deployment/services/zone-manager.md#postgis-setup](docs/deployment/services/zone-manager.md#postgis-setup)

3. **[ ] Zone editor UI deployment**
   - **Metryka**: Web UI accessible on Nebula
   - **Walidacja**: Browse to http://nebula:8015
   - **Procedura**: [docs/deployment/services/zone-manager.md#ui-deployment](docs/deployment/services/zone-manager.md#ui-deployment)

4. **[ ] Integration z detection services**
   - **Metryka**: Zones applied to all detectors
   - **Walidacja**: Test zone filtering in detection
   - **Procedura**: [docs/deployment/services/zone-manager.md#integration](docs/deployment/services/zone-manager.md#integration)

5. **[ ] Performance test z zones**
   - **Metryka**: <5ms zone check overhead
   - **Walidacja**: Benchmark with/without zones
   - **Procedura**: [docs/deployment/services/zone-manager.md#performance-testing](docs/deployment/services/zone-manager.md#performance-testing)

### **🚀 JEDNA KOMENDA DO WYKONANIA:**
```bash
# Cały Blok 5 wykonuje się automatycznie:
git push origin main
```

### **📋 Walidacja sukcesu:**
```bash
# Sprawdź deployment:
curl http://nebula:8015/api/health

# Open zone editor:
open http://nebula:8015

# Test zone API:
curl http://nebula:8015/api/zones
```

### **🔗 Linki do procedur:**
- **Deployment Guide**: [docs/deployment/services/zone-manager.md](docs/deployment/services/zone-manager.md)
- **Quick Start**: [docs/deployment/quick-start.md](docs/deployment/quick-start.md)
- **Troubleshooting**: [docs/deployment/troubleshooting/common-issues.md](docs/deployment/troubleshooting/common-issues.md)

### **🔍 Metryki sukcesu bloku:**
- ✅ Zone manager API operational
- ✅ Web UI for zone editing accessible
- ✅ PostGIS spatial queries working
- ✅ Zones integrated with all detectors
- ✅ <5ms overhead per frame
- ✅ Zero-downtime deployment via CI/CD

## Następne kroki

Po ukończeniu tego zadania, przejdź do:
→ [../faza-4-integracja/01-mqtt-home-assistant.md](../faza-4-integracja/01-mqtt-home-assistant.md)
