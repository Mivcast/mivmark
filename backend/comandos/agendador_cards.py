from apscheduler.schedulers.blocking import BlockingScheduler
from backend.comandos.gerar_cards_automatico import gerar_atualizacoes

def job_diario():
    print("⏰ Executando geração automática de cards...")
    gerar_atualizacoes()

scheduler = BlockingScheduler()
scheduler.add_job(job_diario, 'cron', hour=6)  # Executa todo dia às 6h da manhã

if __name__ == "__main__":
    print("📅 Agendador de cards iniciado...")
    scheduler.start()
