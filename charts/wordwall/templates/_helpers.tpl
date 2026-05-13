{{/*
Expand the name — required field, fails fast if unset.
*/}}
{{- define "wordwall.name" -}}
{{- required "values.name is required" .Values.name | trunc 63 | trimSuffix "-" }}
{{- end }}

{{- define "wordwall.labels" -}}
app.kubernetes.io/name: {{ include "wordwall.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{- define "wordwall.selectorLabels" -}}
app.kubernetes.io/name: {{ include "wordwall.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}
