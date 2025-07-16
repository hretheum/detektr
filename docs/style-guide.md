# Documentation Style Guide

## General Principles

### Voice and Tone

- **Active voice**: Use active voice when possible
- **Present tense**: Write in present tense
- **Direct**: Be clear and concise
- **Consistent**: Use consistent terminology

### Writing Style

- Use second person ("you") when addressing the reader
- Avoid jargon unless necessary and defined
- Write for your audience's technical level
- Use bullet points and numbered lists for readability

## Formatting Guidelines

### Headers

```markdown
# H1 - Document Title (only one per document)
## H2 - Major sections
### H3 - Subsections
#### H4 - Sub-subsections (avoid going deeper)
```

### Code Blocks

Always specify the language for syntax highlighting:

```markdown
\`\`\`python
def example_function():
    return "Hello, World!"
\`\`\`
```

### Links

- Use descriptive link text
- Prefer relative links for internal documentation
- Include protocol for external links

Good: `[API documentation](../api/overview.md)`
Bad: `[click here](../api/overview.md)`

### Lists

- Use parallel structure in lists
- Use numbered lists for sequences
- Use bullet points for non-sequential items

### Tables

Always include headers and align columns:

| Component | Version | Status |
|-----------|---------|--------|
| Service A | 1.2.3   | Active |
| Service B | 2.0.1   | Active |

### Emphasis

- **Bold** for UI elements and important terms
- *Italic* for emphasis
- `Code` for inline code, commands, and file names

## Document Structure

### Standard Sections

Most documents should include:

1. **Overview**: Brief description of purpose
2. **Prerequisites**: What reader needs first
3. **Main Content**: Step-by-step or conceptual content
4. **Examples**: Practical usage examples
5. **Troubleshooting**: Common issues and solutions
6. **References**: Related documentation

### API Documentation

Follow the [API template](templates/api/api-documentation-template.md) for consistency.

### Runbooks

Use the standardized [runbook template](templates/runbooks/runbook-template.md).

## Language and Grammar

### Capitalization

- Use sentence case for headers
- Capitalize proper nouns (Docker, Kubernetes, Prometheus)
- Use ALL CAPS sparingly for emphasis

### Numbers

- Spell out numbers one through nine
- Use numerals for 10 and above
- Use numerals for technical specifications

### Abbreviations

- Define abbreviations on first use
- Use common abbreviations without definition (API, URL, JSON)
- Maintain consistency throughout document

## Code Examples

### Best Practices

- Test all code examples
- Use realistic data in examples
- Include error handling where appropriate
- Show both input and expected output

### Command Line Examples

```bash
# Show the command prompt
$ kubectl get pods

# Show expected output
NAME                     READY   STATUS    RESTARTS   AGE
app-deployment-xyz123    1/1     Running   0          5m
```

### Configuration Examples

Include complete, working examples:

```yaml
# docker-compose.yml
version: '3.8'
services:
  app:
    image: myapp:latest
    ports:
      - "8080:8080"
    environment:
      - NODE_ENV=production
```

## Special Elements

### Admonitions

Use for important information:

!!! note
    This is supplementary information.

!!! warning
    This could cause issues if not followed.

!!! danger
    This could cause data loss or security issues.

### File Paths

Use forward slashes and start from project root:

- Good: `src/services/detection/models.py`
- Bad: `detection\models.py`

### Version References

Always specify versions when relevant:

- Good: "Python 3.11+"
- Bad: "Python 3"

## Review Checklist

Before publishing documentation:

- [ ] Spell check completed
- [ ] Grammar check completed
- [ ] All links work correctly
- [ ] Code examples tested
- [ ] Formatting consistent
- [ ] Audience-appropriate level
- [ ] Logical flow and structure
- [ ] No sensitive information exposed

## Tools

### Linting

Use Vale for automated style checking:

```bash
vale docs/
```

### Link Checking

```bash
markdown-link-check docs/**/*.md
```

### Spell Check

```bash
aspell check -M document.md
```

## Examples

### Good Example

```markdown
## Installing Dependencies

To install the required dependencies:

1. Ensure you have Python 3.11+ installed
2. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

The installation should complete without errors. You can verify by running:

```bash
python --version
```

```

### Poor Example
```markdown
## Installation

Run this command:
```

pip install -r requirements.txt

```

Make sure python is installed first. Click [here](setup.md) for more info.
```

## Maintenance

### Regular Tasks

- Review style guide quarterly
- Update examples when API changes
- Check for broken links monthly
- Validate code examples with releases

### Version Control

- Document all style guide changes
- Maintain backward compatibility when possible
- Communicate changes to team
