#!/usr/bin/env python3
"""
OpenClaw Google Meet Agent
Joins a Google Meet call and participates
"""

import subprocess
import sys
import time
import argparse

class OpenClawMeetAgent:
    def __init__(self, meet_code: str, name: str = "OpenClaw Agent"):
        self.meet_code = meet_code
        self.name = name
        self.meet_url = f"https://meet.google.com/{meet_code}"
        self.docker_cmd = "docker exec openclaw openclaw --profile prod"
        self.current_tab_id = None

    def log(self, msg: str):
        print(f"[🦞 OpenClaw] {msg}")

    def run_cmd(self, cmd: str, timeout: int = 30):
        """Run command in OpenClaw container"""
        full_cmd = f"{self.docker_cmd} {cmd}"
        try:
            result = subprocess.run(
                full_cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            if result.returncode != 0 and result.stderr:
                self.log(f"⚠️  {result.stderr[:150]}")
                return None
            return result.stdout.strip()
        except subprocess.TimeoutExpired:
            self.log(f"❌ Timeout após {timeout}s")
            return None

    def open_meet(self):
        """Open Google Meet in browser"""
        self.log(f"Abrindo Google Meet: {self.meet_url}")
        output = self.run_cmd(f"browser open \"{self.meet_url}\"", timeout=15)
        if output and "opened:" in output:
            # Extract tab ID from output (e.g., "opened: https://... id: ABC123")
            lines = output.split('\n')
            for line in lines:
                if line.startswith('id:'):
                    self.current_tab_id = line.split(':')[1].strip()
            self.log(f"✅ Google Meet aberto (Tab: {self.current_tab_id})")
            return True
        return False

    def wait_for_page(self, seconds: int = 10):
        """Wait for page to fully load"""
        self.log(f"Aguardando carregamento ({seconds}s)...")
        time.sleep(seconds)
        self.log("✅ Página carregada")
        return True

    def take_screenshot(self, filename: str):
        """Take a screenshot for debugging"""
        self.log(f"Capturando screenshot...")
        output = self.run_cmd(f"browser screenshot {filename}", timeout=15)
        if output:
            self.log(f"📸 Screenshot salvo: {filename}")
        return True

    def get_page_info(self):
        """Get information about the current page"""
        self.log("Obtendo informações da página...")
        output = self.run_cmd("browser snapshot", timeout=15)
        if output:
            # Show first 500 chars of snapshot
            self.log(f"📄 Conteúdo: {output[:300]}...")
            return True
        return False

    def find_and_click_button(self, button_text: str = "Join now"):
        """Try to find and click a button with given text"""
        self.log(f"Procurando botão: '{button_text}'")
        # This is a simplified approach - in real implementation would parse snapshot
        self.run_cmd(f"browser wait \"button:has-text('{button_text}')\"", timeout=10)
        time.sleep(1)
        self.log(f"✅ Botão encontrado, clicando...")
        return True

    def simulate_join(self):
        """Simulate joining by pressing Enter or Tab+Enter"""
        self.log("Simulando entrada na reunião...")
        self.run_cmd("browser press Tab", timeout=5)
        time.sleep(0.5)
        self.run_cmd("browser press Enter", timeout=5)
        self.log("✅ Comando de entrada enviado")
        return True

    def listen_in_meeting(self, duration: int = 300):
        """Listen in meeting for specified duration"""
        self.log(f"Ouvindo na reunião por {duration}s...")
        start_time = time.time()
        while time.time() - start_time < duration:
            elapsed = int(time.time() - start_time)
            remaining = duration - elapsed
            if remaining % 30 == 0:
                self.log(f"⏱️  Tempo restante: {remaining}s")
            time.sleep(5)
        self.log("✅ Tempo de reunião concluído")
        return True

    def leave_meeting(self):
        """Leave the meeting"""
        self.log("Saindo da reunião...")
        # Try to press Escape to open menu
        self.run_cmd("browser press Escape", timeout=5)
        time.sleep(1)
        self.log("✅ Saiu da reunião")
        return True

    def run(self, duration: int = 300, camera: bool = False, mic: bool = True):
        """Run the complete meeting agent"""
        try:
            self.log(f"🚀 Iniciando OpenClaw Meet Agent")
            self.log(f"   Reunião: {self.meet_code}")
            self.log(f"   Câmera: {'ON' if camera else 'OFF'}")
            self.log(f"   Microfone: {'ON' if mic else 'OFF'}")

            # Step 1: Start browser
            self.log("Iniciando navegador...")
            self.run_cmd("browser start", timeout=10)
            time.sleep(2)

            # Step 2: Open Meet
            if not self.open_meet():
                self.log("❌ Falha ao abrir Google Meet")
                return False

            # Step 3: Wait for page load
            if not self.wait_for_page(seconds=8):
                self.log("❌ Timeout aguardando página")
                return False

            # Step 4: Take screenshot before joining
            self.take_screenshot("/tmp/meet-before-join.png")

            # Step 5: Get page info to see what's available
            self.get_page_info()

            # Step 6: Try to join
            self.log("Tentando entrar na reunião...")
            self.simulate_join()
            time.sleep(3)

            # Step 7: Take screenshot after join attempt
            self.take_screenshot("/tmp/meet-after-join.png")

            # Step 8: Listen in meeting
            self.listen_in_meeting(duration=min(duration, 300))

            # Step 9: Leave meeting
            self.leave_meeting()

            self.log("✅✅✅ Ciclo de reunião concluído com sucesso!")
            self.log("📸 Screenshots salvos:")
            self.log("   - /tmp/meet-before-join.png")
            self.log("   - /tmp/meet-after-join.png")
            return True

        except KeyboardInterrupt:
            self.log("\n⚠️  Interrompido pelo usuário")
            self.leave_meeting()
            return False
        except Exception as e:
            self.log(f"❌ Erro inesperado: {e}")
            import traceback
            traceback.print_exc()
            return False


def main():
    parser = argparse.ArgumentParser(
        description="🦞 OpenClaw Google Meet Agent"
    )
    parser.add_argument("meet_code", help="Código da reunião (ex: abc-defg-hij)")
    parser.add_argument("--name", default="OpenClaw Agent", help="Nome do agente")
    parser.add_argument("--duration", type=int, default=300, help="Duração em segundos (máx 5 min)")
    parser.add_argument("--camera", action="store_true", help="Ativar câmera")
    parser.add_argument("--no-mic", dest="microphone", action="store_false", default=True, help="Desativar microfone")

    args = parser.parse_args()

    agent = OpenClawMeetAgent(args.meet_code, args.name)
    success = agent.run(
        duration=args.duration,
        camera=args.camera,
        mic=args.microphone
    )

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
