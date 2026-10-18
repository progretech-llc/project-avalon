module github.com/progretech-llc/project-avalon

go 1.24.0

require (
	github.com/gorilla/websocket v1.5.3
	go.autonomous.ai/os v0.0.0
)

require github.com/goccy/go-yaml v1.18.0 // indirect

replace go.autonomous.ai/os => ./.deps/lampos
