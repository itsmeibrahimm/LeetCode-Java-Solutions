{{/*
For local web-deployment, export RUNTIME_PATH to be mounted read-only at /srv/runtime/current.
Defaults to an emptyDir.
See https://kubernetes.io/docs/concepts/storage/volumes/#types-of-volumes
*/}}
{{- define "payment-service.volumes.runtime" }}
  {{- if .Values.web.runtime.hostPath }}
        hostPath:
          path: {{ .Values.web.runtime.hostPath }}
  {{- else }}
        emptyDir: {}
  {{- end }}
{{- end }}

{{/*
For non-local web-deployment, include a runtime container to refresh runtime variables every minute.
*/}}
{{- define "payment-service.containers.runtime" }}
  {{- if .Values.web.runtime.containerEnabled }}
      - name: runtime
        image: ddartifacts-docker.jfrog.io/runtime:latest
        imagePullPolicy: Always
        resources:
          requests:
            cpu: 25m
            memory: 128Mi
          limits:
            cpu: 25m
            memory: 128Mi
        envFrom:
        - configMapRef:
            name: global-runtime-environment
        volumeMounts:
        - name: runtime-volume
          mountPath: /srv/runtime
  {{- end }}
{{- end }}
