{#
  dbt's default behavior concatenates the profile's target schema with any
  custom schema set in a model's config (e.g. "public" + "marts" ->
  "public_marts"). That's intentional upstream (keeps per-developer schemas
  separate in a shared warehouse) but not what we want here: we want the
  `+schema: staging` / `+schema: marts` config in dbt_project.yml to mean
  exactly that schema name. Overriding this macro is the documented way to
  change that behavior project-wide.
#}
{% macro generate_schema_name(custom_schema_name, node) -%}
    {%- if custom_schema_name is none -%}
        {{ target.schema }}
    {%- else -%}
        {{ custom_schema_name | trim }}
    {%- endif -%}
{%- endmacro %}
