# Faza 6 / Zadanie 4: UI/Dashboard do zarządzania systemem

## Cel zadania

Stworzyć intuicyjny interfejs webowy do zarządzania systemem detekcji z podglądem na żywo, edytorem reguł i pełną kontrolą.

## Blok 0: Prerequisites check

#### Zadania atomowe

1. **[ ] Frontend framework decision**
   - **Metryka**: Framework chosen and justified
   - **Walidacja**:

     ```bash
     # Test framework setup
     npx create-react-app test-ui --template typescript
     # or
     npm create vue@latest test-ui -- --typescript
     # Verify builds successfully
     ```

   - **Czas**: 0.5h

2. **[ ] API endpoints available**
   - **Metryka**: Management API ready
   - **Walidacja**:

     ```bash
     curl http://localhost:8000/api/v1/health
     curl http://localhost:8000/api/v1/cameras
     curl http://localhost:8000/api/v1/automations
     # All return 200 OK
     ```

   - **Czas**: 0.5h

## Dekompozycja na bloki zadań

### Blok 1: Core UI components

#### Zadania atomowe

1. **[ ] Live camera view z bounding boxes**
   - **Metryka**: Real-time video with overlays
   - **Walidacja**:

     ```typescript
     // Component renders video stream
     const stream = useCameraStream('front-door');
     const detections = useDetections('front-door');
     assert(stream.fps >= 10);
     assert(detections.length >= 0);
     // Bounding boxes rendered correctly
     ```

   - **Czas**: 3h

2. **[ ] System health dashboard**
   - **Metryka**: All services status visible
   - **Walidacja**:

     ```typescript
     const health = useSystemHealth();
     assert(health.services.length > 5);
     assert(health.overall_status in ['healthy', 'degraded', 'error']);
     // Each service shows: status, uptime, metrics
     ```

   - **Czas**: 2h

3. **[ ] Detection history timeline**
   - **Metryka**: Scrollable event history
   - **Walidacja**:

     ```typescript
     const events = useDetectionHistory({ hours: 24 });
     assert(events.length > 0);
     // Each event has: timestamp, type, camera, confidence
     // Click event → see video clip
     ```

   - **Czas**: 2.5h

#### Metryki sukcesu bloku

- Live view working
- Health visible
- History browsable

### Blok 2: Automation management

#### Zadania atomowe

1. **[ ] Rule editor with validation**
   - **Metryka**: Visual rule builder
   - **Walidacja**:

     ```typescript
     const editor = useRuleEditor();
     const rule = editor.createRule({
       trigger: 'motion_detected',
       conditions: [{entity: 'sun', state: 'below_horizon'}],
       actions: [{service: 'light.turn_on'}]
     });
     assert(rule.isValid());
     assert(editor.validateRule(rule).errors.length === 0);
     ```

   - **Czas**: 3h

2. **[ ] Automation testing interface**
   - **Metryka**: Test rules before activation
   - **Walidacja**:

     ```typescript
     const tester = useAutomationTester();
     const result = await tester.simulate(automation, mockData);
     assert(result.would_trigger === true);
     assert(result.actions_would_execute.length > 0);
     ```

   - **Czas**: 2h

3. **[ ] Enable/disable controls**
   - **Metryka**: Quick automation control
   - **Walidacja**:

     ```typescript
     const controls = useAutomationControls();
     await controls.toggle('morning_routine');
     assert(controls.getStatus('morning_routine') === 'disabled');
     // Change reflected immediately
     ```

   - **Czas**: 1.5h

#### Metryki sukcesu bloku

- Rules editable
- Testing possible
- Easy control

### Blok 3: Responsive design and deployment

#### Zadania atomowe

1. **[ ] Mobile responsive layout**
   - **Metryka**: Works on phone/tablet
   - **Walidacja**:

     ```typescript
     // Test responsive breakpoints
     const breakpoints = {
       mobile: 375,
       tablet: 768,
       desktop: 1024
     };
     // All layouts render correctly
     ```

   - **Czas**: 2h

2. **[ ] Docker deployment**
   - **Metryka**: Containerized UI
   - **Walidacja**:

     ```bash
     docker build -t detektor-ui .
     docker run -p 3001:80 detektor-ui
     curl http://localhost:3001
     # UI accessible
     ```

   - **Czas**: 1.5h

#### Metryki sukcesu bloku

- Mobile friendly
- Containerized
- Deploy ready

## Całościowe metryki sukcesu zadania

1. **Usability**: Non-technical users can manage
2. **Performance**: UI responds <200ms
3. **Coverage**: All major functions accessible

## Deliverables

1. `/ui/` - Frontend application code
2. `/ui/Dockerfile` - Container configuration
3. `/api/management/` - Management API endpoints
4. `/docs/ui-guide.md` - User guide
5. `/nginx/ui.conf` - Reverse proxy config

## Narzędzia

- **React/Vue**: Frontend framework
- **TypeScript**: Type safety
- **WebSocket**: Real-time updates
- **Chart.js**: Visualizations

## Zależności

- **Wymaga**:
  - Management API ready
  - WebSocket support
- **Blokuje**: End user adoption

## Ryzyka i mitigacje

| Ryzyko | Prawdopodobieństwo | Wpływ | Mitigacja | Early Warning |
|--------|-------------------|-------|-----------|---------------|
| Browser compatibility | Niskie | Średni | Modern browsers only, polyfills | User agent stats |
| Real-time performance | Średnie | Wysoki | WebSocket optimization, throttling | UI lag >500ms |

## Rollback Plan

1. **Detekcja problemu**:
   - UI not loading
   - Features broken
   - Performance issues

2. **Kroki rollback**:
   - [ ] Restore previous UI version
   - [ ] Clear browser cache
   - [ ] Use fallback static UI
   - [ ] Direct API access as backup

3. **Czas rollback**: <5 min

## Blok 5: DEPLOYMENT NA SERWERZE NEBULA

### 🎯 **UNIFIED CI/CD DEPLOYMENT**

> **📚 Deployment dla tego serwisu jest zautomatyzowany przez zunifikowany workflow CI/CD.**

### Kroki deployment

1. **[ ] Przygotowanie serwisu do deployment**
   - **Metryka**: Management UI dodany do workflow matrix
   - **Walidacja**:
     ```bash
     # Sprawdź czy serwis jest w .github/workflows/deploy-self-hosted.yml
     grep "management-ui" .github/workflows/deploy-self-hosted.yml
     ```
   - **Dokumentacja**: [docs/deployment/guides/new-service.md](../../deployment/guides/new-service.md)

2. **[ ] Build frontend assets**
   - **Metryka**: Production build zoptymalizowany
   - **Konfiguracja**:
     ```dockerfile
     # Multi-stage build dla React/Vue
     FROM node:18 as builder
     WORKDIR /app
     COPY package*.json ./
     RUN npm ci
     COPY . .
     RUN npm run build

     FROM nginx:alpine
     COPY --from=builder /app/dist /usr/share/nginx/html
     ```

3. **[ ] Deploy przez GitHub Actions**
   - **Metryka**: Automated deployment via git push
   - **Komenda**:
     ```bash
     git add .
     git commit -m "feat: deploy management-ui for system administration"
     git push origin main
     ```
   - **Monitorowanie**: https://github.com/hretheum/bezrobocie/actions

### **📋 Walidacja po deployment:**

```bash
# 1. Sprawdź dostępność UI
curl -I http://nebula:8080

# 2. Test static assets
curl http://nebula:8080/static/js/main.js | head -1

# 3. Sprawdź WebSocket endpoint
curl -i -N -H "Connection: Upgrade" -H "Upgrade: websocket" \
  http://nebula:8080/ws

# 4. Test API integration
curl http://nebula:8080/api/status

# 5. Otwórz UI w przeglądarce
open http://nebula:8080
```

### **🔗 Dokumentacja:**
- **Unified Deployment Guide**: [docs/deployment/README.md](../../deployment/README.md)
- **New Service Guide**: [docs/deployment/guides/new-service.md](../../deployment/guides/new-service.md)
- **Frontend Build Guide**: [docs/deployment/guides/frontend-services.md](../../deployment/guides/frontend-services.md)

### **🔍 Metryki sukcesu bloku:**
- ✅ Serwis w workflow matrix `.github/workflows/deploy-self-hosted.yml`
- ✅ UI accessible at http://nebula:8080
- ✅ All pages loading <2s
- ✅ WebSocket connections stable
- ✅ API calls authenticated
- ✅ Mobile responsive design
- ✅ Zero-downtime deployment

## Następne kroki

Po ukończeniu tego zadania, przejdź do:
→ [05-consolidated-dashboard.md](./05-consolidated-dashboard.md)
