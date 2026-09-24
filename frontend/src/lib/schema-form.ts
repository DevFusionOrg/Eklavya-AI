import { z } from "zod";
import type { FormProperty, SchemeForm } from "./api";

export type WizardStep = {
  id: string;
  label: string;
  fields: string[];
};

function propertySchema(property: FormProperty) {
  let schema: z.ZodTypeAny;
  if (property.enum?.length) schema = z.enum(property.enum as [string, ...string[]]);
  else if (property.type === "number") schema = z.number();
  else if (property.type === "integer") schema = z.number().int();
  else if (property.type === "boolean") schema = z.boolean();
  else if (property.type === "array") schema = z.array(z.unknown());
  else if (property.type === "object") schema = z.record(z.unknown());
  else schema = z.string();
  if (property.type === "string" && property.minLength !== undefined) {
    schema = (schema as z.ZodString).min(property.minLength);
  }
  if (property.type === "string" && property.maxLength !== undefined) {
    schema = (schema as z.ZodString).max(property.maxLength);
  }
  if (property.type !== "string" && property.minimum !== undefined) {
    schema = (schema as z.ZodNumber).min(property.minimum);
  }
  if (property.type !== "string" && property.maximum !== undefined) {
    schema = (schema as z.ZodNumber).max(property.maximum);
  }
  return schema;
}

export function schemaToZod(form: SchemeForm) {
  const properties = form.form_schema.properties ?? {};
  const required = new Set(form.form_schema.required ?? []);
  const shape: Record<string, z.ZodTypeAny> = {};
  for (const [name, property] of Object.entries(properties)) {
    const schema = propertySchema(property);
    shape[name] = required.has(name) ? schema : schema.optional();
  }
  return z.object(shape);
}

export function stepsFromSchema(form: SchemeForm): WizardStep[] {
  const properties = form.form_schema.properties ?? {};
  const configured = form.ui_hints.steps;
  if (Array.isArray(configured)) {
    const configuredSteps = configured.filter(
      (step): step is { id: string; label: string; fields: string[] } =>
        typeof step === "object" &&
        step !== null &&
        typeof (step as { id?: unknown }).id === "string" &&
        Array.isArray((step as { fields?: unknown }).fields),
    );
    if (configuredSteps.length) return configuredSteps;
  }
  const grouped = new Map<string, string[]>();
  for (const [name, property] of Object.entries(properties)) {
    const step = property["ui:step"] ?? "application";
    grouped.set(step, [...(grouped.get(step) ?? []), name]);
  }
  return Array.from(grouped, ([id, fields]) => ({
    id,
    label: id.replace(/[-_]/g, " ").replace(/^\w/, (letter) => letter.toUpperCase()),
    fields,
  }));
}

export function displayLabel(name: string, property: FormProperty) {
  return property.title ?? name.replace(/[-_]/g, " ").replace(/^\w/, (letter) => letter.toUpperCase());
}
