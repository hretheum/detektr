# Stakeholder Review Notes - Requirements v1.0

## Meeting Details
- **Date**: 2025-07-15
- **Participants**: Self (wearing different hats)
- **Duration**: 1 hour review session

## Key Decisions Made

### 1. Scope Clarifications
- **Decision**: Focus on local processing, no cloud dependencies for core features
- **Rationale**: Privacy, latency, and hobby project constraints

### 2. Priority Adjustments
- **Decision**: Voice features moved to SHOULD/COULD
- **Rationale**: Visual detection is primary use case, voice is nice-to-have

### 3. Hardware Assumptions
- **Decision**: Optimize for GTX 4070 Super as baseline
- **Rationale**: Available hardware, good balance of performance/cost

### 4. Integration Strategy
- **Decision**: MQTT as primary integration protocol with Home Assistant
- **Rationale**: Standard in home automation, well-supported

### 5. Security Approach
- **Decision**: SOPS + age for secrets, no cloud key management
- **Rationale**: Simple, secure, appropriate for home use

## Open Questions Resolved

1. **Q**: How many cameras realistically?
   **A**: 4 cameras standard, 8 max (GPU constraint)

2. **Q**: Store video or just metadata?
   **A**: Metadata only, thumbnails for events

3. **Q**: Which LLM for intent?
   **A**: Start with OpenAI API, design for swappable

4. **Q**: Backup strategy?
   **A**: Local only, manual offsite optional

## Future Enhancements (Post-v1.0)
- WebRTC for live streaming
- Multi-site deployment
- Advanced analytics
- Custom model training

## Sign-off
Requirements approved for implementation. No blocking issues identified.