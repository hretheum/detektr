"""
Detektor - System Detekcji i Automatyzacji Wizyjnej

System wykorzystujacy kamery IP i AI do wykrywania obiektow,
rozpoznawania twarzy oraz automatyzacji dzialan w smart home.

Architektura: Clean Architecture + Domain-Driven Design
Bounded Contexts:
- monitoring: Observability (metrics, traces, logs)
- detection: AI/ML detection services
- management: Configuration and camera management
- automation: Home Assistant integration
- integration: External systems integration
"""

__version__ = "0.1.0"
__author__ = "Detektor Team"
