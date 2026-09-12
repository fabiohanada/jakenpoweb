from django.db import models
from django.contrib.auth.models import User

class Sala(models.Model):
    jogador1 = models.ForeignKey(User, related_name='jogos_como_j1', on_delete=models.CASCADE)
    jogador2 = models.ForeignKey(User, related_name='jogos_como_j2', on_delete=models.SET_NULL, null=True, blank=True)
    
    escolha_j1 = models.CharField(max_length=10, blank=True, null=True)
    escolha_j2 = models.CharField(max_length=10, blank=True, null=True)
    
    status = models.CharField(max_length=30, default='aguardando_oponente')
    resultado = models.CharField(max_length=20, blank=True, null=True)
    
    criado_em = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        j2_nome = self.jogador2.username if self.jogador2 else "Aguardando..."
        return f"Sala {self.id}: {self.jogador1.username} vs {j2_nome}"