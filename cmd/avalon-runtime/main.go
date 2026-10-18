// Avalon hosts the selected unmodified LampOS gateway with per-user state.
package main

import (
	"context"
	"encoding/json"
	"errors"
	"flag"
	"log"
	"net"
	"os"
	"os/signal"
	"path/filepath"
	"syscall"
	"time"

	claude "go.autonomous.ai/os/runtimes/claudecode/gatewayd"
	codex "go.autonomous.ai/os/runtimes/codex/gatewayd"
	"go.autonomous.ai/os/runtimes/opencode/gatewayd"
)

type settings struct {
	Platform  string `json:"platform"`
	Token     string `json:"token"`
	Binary    string `json:"binary"`
	Workspace string `json:"workspace"`
}

func main() {
	state := flag.String("state", "", "private Avalon runtime directory")
	flag.Parse()
	if *state == "" || !filepath.IsAbs(*state) {
		log.Fatal("--state must be an absolute path")
	}
	lock, err := os.OpenFile(filepath.Join(*state, "runtime.lock"), os.O_CREATE|os.O_RDWR, 0600)
	if err != nil {
		log.Fatal(err)
	}
	defer lock.Close()
	if err := syscall.Flock(int(lock.Fd()), syscall.LOCK_EX|syscall.LOCK_NB); err != nil {
		log.Fatal("Avalon runtime already owned: ", err)
	}
	raw, err := os.ReadFile(filepath.Join(*state, "gateway.json"))
	if err != nil {
		log.Fatal(err)
	}
	var cfg settings
	if err := json.Unmarshal(raw, &cfg); err != nil {
		log.Fatal(err)
	}
	if len(cfg.Token) < 32 || !filepath.IsAbs(cfg.Binary) {
		log.Fatal("invalid gateway configuration")
	}
	if cfg.Platform == "" {
		cfg.Platform = "opencode"
	}
	agentHome := filepath.Join(*state, "agent-home")
	if cfg.Platform == "opencode" {
		for key, value := range map[string]string{
			"XDG_CONFIG_HOME":                 filepath.Join(agentHome, ".config"),
			"XDG_DATA_HOME":                   filepath.Join(agentHome, ".local/share"),
			"XDG_CACHE_HOME":                  filepath.Join(agentHome, ".cache"),
			"XDG_STATE_HOME":                  filepath.Join(agentHome, ".local/state"),
			"OPENCODE_CONFIG":                 filepath.Join(agentHome, ".config/opencode/opencode.json"),
			"OPENCODE_CONFIG_DIR":             filepath.Join(agentHome, ".config/opencode"),
			"OPENCODE_DISABLE_PROJECT_CONFIG": "true", "OPENCODE_DISABLE_CLAUDE_CODE": "true",
			"OPENCODE_DISABLE_AUTOUPDATE": "true",
		} {
			if err := os.Setenv(key, value); err != nil {
				log.Fatal(err)
			}
		}
		// Do not inherit inline configuration or keys from the launching agent.
		for _, key := range []string{"OPENCODE_CONFIG_CONTENT", "OPENAI_API_KEY", "ANTHROPIC_API_KEY", "OPENROUTER_API_KEY"} {
			os.Unsetenv(key)
		}
	}
	workspace := cfg.Workspace
	if workspace == "" {
		workspace = filepath.Join(*state, "workspace")
	}
	if !filepath.IsAbs(workspace) {
		log.Fatal("Workspace must be absolute")
	}
	ln, err := net.Listen("tcp", "127.0.0.1:18893")
	if err != nil {
		log.Fatal(err)
	}
	ctx, cancel := signal.NotifyContext(context.Background(), os.Interrupt, syscall.SIGTERM)
	defer cancel()
	var server interface{ Serve(context.Context) error }
	switch cfg.Platform {
	case "codex":
		home, err := os.UserHomeDir()
		if err != nil {
			log.Fatal(err)
		}
		server = codex.New(codex.Config{Token: cfg.Token, CodexBin: cfg.Binary, Home: home, CodexHome: filepath.Join(home, ".codex"), Workspace: workspace, SessionFile: filepath.Join(*state, "session.json"), AttachDir: filepath.Join(*state, "attachments"), TurnTimeout: 300 * time.Second, UseAppServer: true}, ln)
	case "claudecode":
		home, err := os.UserHomeDir()
		if err != nil {
			log.Fatal(err)
		}
		server = claude.New(claude.Config{Token: cfg.Token, ClaudeBin: cfg.Binary, Home: home, Workspace: workspace, SessionFile: filepath.Join(*state, "session.json"), RestartBackoff: time.Second}, ln)
	case "opencode":
		server = gatewayd.New(gatewayd.Config{
			Token: cfg.Token, Bin: cfg.Binary, Home: filepath.Join(*state, "agent-home"),
			Workspace: workspace, SessionFile: filepath.Join(*state, "session.json"),
			AttachDir: filepath.Join(*state, "attachments"), TurnTimeout: 300 * time.Second,
		}, ln)
	default:
		log.Fatal("Unsupported native platform: ", cfg.Platform)
	}
	if err := server.Serve(ctx); err != nil && !errors.Is(err, context.Canceled) {
		log.Fatal(err)
	}
}
