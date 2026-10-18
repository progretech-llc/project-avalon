// Run a bounded, text-only turn through the real LampOS gateway.
package main

import (
	"crypto/rand"
	"encoding/json"
	"flag"
	"fmt"
	"log"
	"net/http"
	"os"
	"path/filepath"
	"strings"
	"time"

	"github.com/gorilla/websocket"
)

func main() {
	state := flag.String("state", "", "Avalon private runtime directory")
	flag.Parse()
	raw, err := os.ReadFile(filepath.Join(*state, "gateway.json"))
	if err != nil {
		log.Fatal(err)
	}
	var cfg struct {
		Token string `json:"token"`
	}
	if err := json.Unmarshal(raw, &cfg); err != nil {
		log.Fatal(err)
	}
	header := http.Header{}
	header.Set("Authorization", "Bearer "+cfg.Token)
	var conn *websocket.Conn
	deadline := time.Now().Add(5 * time.Second)
	for {
		conn, _, err = (&websocket.Dialer{HandshakeTimeout: time.Second}).Dial("ws://127.0.0.1:18893/opencode/ws/", header)
		if err == nil {
			break
		}
		if time.Now().After(deadline) {
			log.Fatal(err)
		}
		time.Sleep(100 * time.Millisecond)
	}
	defer conn.Close()
	conn.SetReadLimit(1024 * 1024)
	conn.SetReadDeadline(time.Now().Add(150 * time.Second))
	var frame map[string]any
	if err := conn.ReadJSON(&frame); err != nil {
		log.Fatal(err)
	}
	if frame["type"] != "bridge.status" || frame["state"] != "ready" {
		log.Fatal("gateway did not report status")
	}
	requestID := "avalon-foundation-" + rand.Text()
	start := time.Now()
	err = conn.WriteJSON(map[string]any{"type": "message.send", "id": requestID, "run_id": requestID, "payload": map[string]any{"content": "Compute 19 + 23. Reply exactly AVALON_42. Do not use tools."}})
	if err != nil {
		log.Fatal(err)
	}
	text := ""
	count := 0
	for {
		frame = nil
		if err := conn.ReadJSON(&frame); err != nil {
			log.Fatal(err)
		}
		count++
		if count > 2000 {
			log.Fatal("event limit exceeded")
		}
		if frame["request_id"] != requestID || frame["run_id"] != requestID {
			continue
		}
		if frame["type"] == "bridge.error" || frame["type"] == "error" {
			log.Fatal("runtime failed: ", frame["error"])
		}
		if frame["type"] == "text" {
			if part, ok := frame["part"].(map[string]any); ok {
				s, _ := part["text"].(string)
				text += s
			}
		}
		if frame["type"] == "session.idle" {
			break
		}
	}
	if strings.TrimSpace(text) != "AVALON_42" {
		log.Fatal("reply did not pass challenge: ", text)
	}
	result := map[string]any{"passed": true, "transport": "LampOS OpenCode gateway", "answer": strings.TrimSpace(text), "events": count, "elapsed_ms": time.Since(start).Milliseconds()}
	output, _ := json.MarshalIndent(result, "", "  ")
	fmt.Println(string(output))
}
