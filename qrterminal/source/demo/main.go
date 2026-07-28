package main

import (
	"fmt"
	"os"

	"github.com/mdp/qrterminal/v3"
)

func main() {
	text := "https://example.com"

	fmt.Println("=== GO SOURCE FULL-BLOCK DEMO ===")
	qrterminal.Generate(text, qrterminal.L, os.Stdout)

	fmt.Println("\n=== GO SOURCE HALF-BLOCK DEMO ===")
	qrterminal.GenerateHalfBlock(text, qrterminal.L, os.Stdout)
}
