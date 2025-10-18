class Fİnder:
    def __init__(self):
        pass

    async def main(self, target):

        targets = [
            "dataController.balancePositionSystem.getBalance",
            "dataController.balancePositionSystem.getPositions",
        ]
        for target in targets:

            result = subprocess.run(
                ["pgrep", "-af", target], capture_output=True, text=True
            )

            if result.stdout:
                lines = result.stdout.strip().split("\n")
                pids = [line.split()[0] for line in lines]  # PID sütunu

                print(f"{target} için bulunan PID'ler: {pids}")
                ender(int(pids[0]))

            else:
                print(f"{target} için hiçbir process bulunamadı.")


class killer:
    """
    PID sonlandırıcı sınıfı
    """

    def __init__(self):
        pass

    async def main(self, pid):
        try:
            process = psutil.Process(pid)
            process.terminate()  # SIGTERM gönderir
            process.wait(timeout=3)  # 3 saniye bekle
            print(f"PID {pid} başarıyla sonlandırıldı.")
        except psutil.NoSuchProcess:
            print(f"PID {pid} bulunamadı.")
        except psutil.AccessDenied:
            print(f"PID {pid} için yeterli izin yok.")
        except psutil.TimeoutExpired:
            process.kill()  # Zorla sonlandır (SIGKILL)
            print(f"PID {pid} zorla sonlandırıldı.")