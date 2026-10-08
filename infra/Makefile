# SAM makefile build (template.yaml BuildMethod: makefile). Runs from the repo root (CodeUri ..) and
# packages only backend/ (without tests), config/ and data/, so app/ and node_modules never reach Lambda.
PKG = cp -R backend config data "$(ARTIFACTS_DIR)/" && rm -rf "$(ARTIFACTS_DIR)/backend/tests" && find "$(ARTIFACTS_DIR)" -name __pycache__ -prune -exec rm -rf {} +

build-AdvisorFunction build-VoiceFunction build-IngestFunction build-AuthorizerFunction:
	$(PKG)
