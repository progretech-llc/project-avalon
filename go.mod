module github.com/progretech-llc/project-avalon

go 1.24.0

require (
	github.com/gorilla/websocket v1.5.3
	go.autonomous.ai/os v0.0.0
)

require (
	github.com/bwmarrin/discordgo v0.29.0 // indirect
	github.com/creack/pty v1.1.24 // indirect
	github.com/eclipse/paho.golang v0.23.0 // indirect
	github.com/goccy/go-yaml v1.18.0 // indirect
	github.com/google/wire v0.7.0 // indirect
	github.com/joho/godotenv v1.5.1 // indirect
	github.com/pelletier/go-toml/v2 v2.2.4 // indirect
	golang.org/x/crypto v0.47.0 // indirect
	golang.org/x/net v0.49.0 // indirect
)

replace go.autonomous.ai/os => ./.deps/lampos
