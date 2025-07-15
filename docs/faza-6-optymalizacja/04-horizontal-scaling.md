# Faza 6 / Zadanie 4: Scaling to Multiple Nodes

## Cel zadania
Przekształcić system w skalowalną horyzontalnie architekturę zdolną do obsługi 100+ kamer poprzez dystrybucję obciążenia między wieloma węzłami.

## Blok 0: Prerequisites check

#### Zadania atomowe:
1. **[ ] Kubernetes cluster operational**
   - **Metryka**: K8s cluster z min. 3 worker nodes
   - **Walidacja**: 
     ```bash
     # Check cluster nodes
     kubectl get nodes | grep Ready | wc -l
     # Should return >= 3
     kubectl top nodes  # All nodes < 80% CPU
     ```
   - **Czas**: 0.5h

2. **[ ] Service mesh ready**
   - **Metryka**: Istio/Linkerd installed
   - **Walidacja**: 
     ```bash
     # Check service mesh
     kubectl get pods -n istio-system | grep Running | wc -l
     # Should return > 5
     istioctl analyze  # No critical issues
     ```
   - **Czas**: 0.5h

## Dekompozycja na bloki zadań

### Blok 1: Stateless service refactoring

#### Zadania atomowe:
1. **[ ] Extract shared state to external stores**
   - **Metryka**: Zero in-memory shared state
   - **Walidacja**: 
     ```python
     from state_analyzer import scan_services
     analysis = scan_services()
     assert len(analysis.stateful_components) == 0
     assert all(s.uses_external_state for s in analysis.services)
     ```
   - **Czas**: 3h

2. **[ ] Session affinity removal**
   - **Metryka**: Any instance can handle any request
   - **Walidacja**: 
     ```bash
     # Test round-robin with chaos
     ./scripts/test_stateless.sh --kill-random-pods
     # All requests should succeed
     grep "failed: 0" test_results.log
     ```
   - **Czas**: 2h

3. **[ ] Distributed locking implementation**
   - **Metryka**: Concurrent operations safe
   - **Walidacja**: 
     ```python
     lock_test = run_distributed_lock_test(
         concurrent_workers=50,
         operations=1000
     )
     assert lock_test.race_conditions == 0
     assert lock_test.deadlocks == 0
     ```
   - **Czas**: 2.5h

#### Metryki sukcesu bloku:
- Services fully stateless
- Ready for replication
- Concurrency safe

### Blok 2: Load distribution

#### Zadania atomowe:
1. **[ ] Camera-to-node sharding**
   - **Metryka**: Even distribution of cameras
   - **Walidacja**: 
     ```python
     distribution = analyze_camera_distribution()
     assert distribution.std_deviation < 0.1  # Even spread
     assert all(n.camera_count > 0 for n in distribution.nodes)
     assert distribution.rebalance_needed == False
     ```
   - **Czas**: 2.5h

2. **[ ] Work queue partitioning**
   - **Metryka**: Parallel processing without conflicts
   - **Walidacja**: 
     ```python
     queue_test = test_partitioned_queues(partitions=10)
     assert queue_test.message_ordering_preserved == True
     assert queue_test.partition_efficiency > 0.9
     assert queue_test.cross_partition_traffic == 0
     ```
   - **Czas**: 2h

3. **[ ] Dynamic load balancing**
   - **Metryka**: Automatic rebalancing under load
   - **Walidacja**: 
     ```bash
     # Start uneven load test
     ./load_test.sh --uneven --duration=300
     # Check rebalancing
     kubectl logs -l app=load-balancer | grep "rebalanced" | wc -l
     # Should show rebalancing events
     ```
   - **Czas**: 2h

#### Metryki sukcesu bloku:
- Load evenly distributed
- Auto-rebalancing active
- No hotspots

### Blok 3: Kubernetes deployment

#### Zadania atomowe:
1. **[ ] Helm charts creation**
   - **Metryka**: Parameterized deployments
   - **Walidacja**: 
     ```bash
     # Lint helm charts
     helm lint charts/detektor
     # Dry run deployment
     helm install detektor charts/detektor --dry-run --debug
     # Template generation works
     helm template charts/detektor | kubectl apply --dry-run=client -f -
     ```
   - **Czas**: 2.5h

2. **[ ] Horizontal Pod Autoscaler**
   - **Metryka**: Auto-scaling based on load
   - **Walidacja**: 
     ```yaml
     # Check HPA configured
     kubectl get hpa -o yaml | grep -E "minReplicas: 3|maxReplicas: 50"
     # Test scaling
     kubectl run -i --tty load-generator --image=busybox /bin/sh
     # Generate load and verify scaling
     ```
   - **Czas**: 2h

3. **[ ] Pod disruption budgets**
   - **Metryka**: High availability maintained
   - **Walidacja**: 
     ```bash
     # Check PDBs exist
     kubectl get pdb | grep detektor
     # Verify minimum available
     kubectl get pdb detektor-detection -o jsonpath='{.spec.minAvailable}'
     # Should return 2 or more
     ```
   - **Czas**: 1.5h

#### Metryki sukcesu bloku:
- K8s deployment ready
- Auto-scaling configured
- HA guaranteed

### Blok 4: Multi-node testing

#### Zadania atomowe:
1. **[ ] 100 camera load test**
   - **Metryka**: System handles 100 concurrent cameras
   - **Walidacja**: 
     ```python
     load_test = run_scaled_test(cameras=100, duration_min=30)
     assert load_test.processed_fps > 2900  # ~29 FPS per camera
     assert load_test.failed_frames_percent < 0.1
     assert load_test.p99_latency_ms < 200
     ```
   - **Czas**: 2.5h

2. **[ ] Node failure resilience**
   - **Metryka**: Zero downtime during node failure
   - **Walidacja**: 
     ```bash
     # Start continuous test
     ./scripts/continuous_test.sh &
     TEST_PID=$!
     # Kill random node
     kubectl drain node-3 --force --delete-emptydir-data
     # Check test still passing
     kill -0 $TEST_PID && echo "Test survived node failure"
     ```
   - **Czas**: 2h

3. **[ ] Scale-up/down testing**
   - **Metryka**: Graceful scaling without data loss
   - **Walidacja**: 
     ```python
     scale_test = test_scaling_operations()
     assert scale_test.scale_up_time_seconds < 60
     assert scale_test.scale_down_graceful == True
     assert scale_test.events_lost == 0
     ```
   - **Czas**: 1.5h

#### Metryki sukcesu bloku:
- 100+ cameras supported
- Fault tolerant
- Elastic scaling

## Całościowe metryki sukcesu zadania

1. **Scalability**: Linear scaling to 100+ cameras
2. **Availability**: 99.9% uptime during scaling
3. **Performance**: <10% overhead from distribution

## Deliverables

1. `/charts/detektor/` - Helm charts for deployment
2. `/configs/k8s/` - Kubernetes manifests
3. `/src/distributed/` - Distribution logic
4. `/scripts/scaling/` - Scaling test suite
5. `/docs/scaling-guide.md` - Operations guide

## Narzędzia

- **Kubernetes**: Container orchestration
- **Helm**: Package management
- **Istio**: Service mesh
- **Prometheus**: Metrics
- **Grafana**: Dashboards

## Zależności

- **Wymaga**: Caching strategy implemented
- **Blokuje**: Production deployment

## Ryzyka i mitigacje

| Ryzyko | Prawdopodobieństwo | Wpływ | Mitigacja | Early Warning |
|--------|-------------------|-------|-----------|---------------|
| Split brain | Niskie | Wysoki | Distributed consensus | Duplicate events |
| Network partitions | Średnie | Wysoki | Retry + circuit breakers | Timeout spikes |
| Resource limits | Średnie | Średni | Resource quotas | OOM kills |

## Rollback Plan

1. **Detekcja problemu**: 
   - Scaling failures
   - Data inconsistency
   - Performance degradation

2. **Kroki rollback**:
   - [ ] Scale down to single node
   - [ ] Disable HPA
   - [ ] Consolidate sharded data
   - [ ] Verify single-node operation

3. **Czas rollback**: <45 min

## Następne kroki

Po ukończeniu tego zadania, przejdź do:
→ [05-production-hardening.md](./05-production-hardening.md)