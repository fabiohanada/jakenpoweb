from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db.models import Q
from .models import Sala
from .forms import RegistroForm
from django.http import JsonResponse
import random

@login_required(login_url='/login/')
def home(request):
    usuario = request.user
    
    # 1. Busca as salas abertas aguardando jogador
    salas_aguardando = Sala.objects.filter(status='aguardando_oponente')
    
    # 2. Busca todas as partidas finalizadas onde o usuário participou
    partidas_finalizadas = Sala.objects.filter(
        (Q(jogador1=usuario) | Q(jogador2=usuario)) & Q(status__in=['finalizado', 'historico'])
    ).order_by('-criado_em')

    # 3. Calcula as estatísticas
    vitorias = 0
    derrotas = 0
    empates = 0

    for partida in partidas_finalizadas:
        if partida.resultado == 'empate':
            empates += 1
        elif (partida.jogador1 == usuario and partida.resultado == 'vitoria_j1') or \
             (partida.jogador2 == usuario and partida.resultado == 'vitoria_j2'):
            vitorias += 1
        else:
            derrotas += 1

    # 4. Envia tudo para a tela
    contexto = {
        'salas': salas_aguardando,
        'vitorias': vitorias,
        'derrotas': derrotas,
        'empates': empates,
        'historico': partidas_finalizadas[:5] # Pega apenas as últimas 5 partidas para não poluir a tela
    }
    
    return render(request, 'jogo/home.html', contexto)

def registrar(request):
    if request.method == 'POST':
        form = RegistroForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.set_password(form.cleaned_data['senha'])
            user.save()
            login(request, user)
            return redirect('home')
    else:
        form = RegistroForm()
    return render(request, 'jogo/registrar.html', {'form': form})

def entrar(request):
    if request.method == 'GET':
        logout(request)
        
    # Lógica de Login
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            return redirect('home')
    else:
        form = AuthenticationForm()

    # Lógica do Ranking Geral (Top 5)
    usuarios = User.objects.all()
    ranking = []
    
    for u in usuarios:
        # Conta quantas vezes o usuário ganhou como Jogador 1 ou Jogador 2
        vitorias_j1 = Sala.objects.filter(jogador1=u, resultado='vitoria_j1').count()
        vitorias_j2 = Sala.objects.filter(jogador2=u, resultado='vitoria_j2').count()
        total_vitorias = vitorias_j1 + vitorias_j2
        
        # Só adiciona ao ranking se tiver pelo menos 1 vitória
        if total_vitorias > 0:
            ranking.append({'nome': u.username, 'vitorias': total_vitorias})
            
    # Ordena a lista do maior número de vitórias para o menor e pega os 5 primeiros
    ranking_ordenado = sorted(ranking, key=lambda x: x['vitorias'], reverse=True)[:5]

    return render(request, 'jogo/login.html', {'form': form, 'ranking': ranking_ordenado})

@login_required
def criar_sala(request):
    if request.method == 'POST':
        # Apaga outras salas vazias que esse usuário criou e abandonou
        Sala.objects.filter(jogador1=request.user, status='aguardando_oponente').delete()
        
        # Cria a nova sala
        sala = Sala.objects.create(jogador1=request.user)
        
        # Redireciona o usuário direto para a sala que ele acabou de criar
        return redirect('entrar_sala', sala_id=sala.id) 
    return render(request, 'jogo/criar_sala.html')

@login_required
def entrar_sala(request, sala_id):
    sala = get_object_or_404(Sala, id=sala_id)
    
    # SEGURANÇA: Se a sala estava em andamento ou finalizada, mas o jogador2 sumiu/saiu
    if sala.status in ['em_andamento', 'finalizado'] and not sala.jogador2:
        sala.status = 'aguardando_oponente'
        sala.escolha_j1 = None
        sala.escolha_j2 = None
        sala.resultado = None
        sala.save()

    # Se a sala está aguardando e o usuário não é o criador, ele entra como jogador 2
    if sala.status == 'aguardando_oponente' and not sala.jogador2 and sala.jogador1 != request.user:
        sala.jogador2 = request.user
        sala.status = 'em_andamento'
        sala.save()
        
    # Se o usuário faz parte da sala, ele vai para a tela de jogo
    if request.user == sala.jogador1 or request.user == sala.jogador2:
        # Se os dois já jogaram, calcula o resultado
        if sala.escolha_j1 and sala.escolha_j2 and sala.status == 'em_andamento':
            j1 = sala.escolha_j1
            j2 = sala.escolha_j2
            
            if j1 == j2:
                sala.resultado = 'empate'
            elif (j1 == 'pedra' and j2 == 'tesoura') or (j1 == 'papel' and j2 == 'pedra') or (j1 == 'tesoura' and j2 == 'papel'):
                sala.resultado = 'vitoria_j1'
            else:
                sala.resultado = 'vitoria_j2'
            sala.status = 'finalizado'
            sala.save()
            
        return render(request, 'jogo/sala.html', {'sala': sala})
    
    return redirect('home')

@login_required
def fazer_jogada(request, sala_id):
    sala = get_object_or_404(Sala, id=sala_id)
    escolha = request.POST.get('escolha')
    
    if request.user == sala.jogador1 and not sala.escolha_j1:
        sala.escolha_j1 = escolha
        sala.save()
    elif request.user == sala.jogador2 and not sala.escolha_j2:
        sala.escolha_j2 = escolha
        sala.save()
        
    return redirect('entrar_sala', sala_id=sala.id)

@login_required
def jogar_novamente(request, sala_id):
    sala = get_object_or_404(Sala, id=sala_id)
    
    if request.user == sala.jogador1 or request.user == sala.jogador2:
        if sala.status == 'finalizado':
            sala.escolha_j1 = None
            
            # Se o oponente for o Computador, ele já faz a nova jogada instantaneamente!
            if sala.jogador2 and sala.jogador2.username == 'Computador':
                sala.escolha_j2 = random.choice(['pedra', 'papel', 'tesoura'])
            else:
                sala.escolha_j2 = None
                
            sala.resultado = None
            sala.status = 'em_andamento'
            sala.save()
            
    return redirect('entrar_sala', sala_id=sala.id)

@login_required
def sair_sala(request, sala_id):
    try:
        sala = Sala.objects.get(id=sala_id)
        if request.user == sala.jogador1 or request.user == sala.jogador2:
            if sala.status == 'finalizado':
                # O jogo acabou! Em vez de apagar, guardamos no histórico.
                sala.status = 'historico'
                sala.save()
            else:
                # Se alguém fugir no meio da partida, aí sim apagamos a sala.
                sala.delete()
    except Sala.DoesNotExist:
        pass
        
    return redirect('home')

@login_required
def status_sala_api(request, sala_id):
    try:
        sala = Sala.objects.get(id=sala_id)
        # Se a sala virou histórico, dizemos ao JavaScript que ela foi encerrada
        if sala.status == 'historico':
            return JsonResponse({'apagada': True})
            
        return JsonResponse({
            'status': sala.status,
            'apagada': False
        })
    except Sala.DoesNotExist:
        return JsonResponse({'apagada': True})

@login_required
def criar_sala_computador(request):
    if request.method == 'POST':
        # Limpa salas vazias abandonadas pelo usuário
        Sala.objects.filter(jogador1=request.user, status='aguardando_oponente').delete()
        
        # O Django procura o usuário "Computador". Se não existir, ele cria na hora!
        bot, created = User.objects.get_or_create(username='Computador')
        
        # Cria a sala, coloca o bot como jogador2 e já sorteia a jogada dele
        sala = Sala.objects.create(
            jogador1=request.user,
            jogador2=bot,
            status='em_andamento',
            escolha_j2=random.choice(['pedra', 'papel', 'tesoura'])
        )
        
        return redirect('entrar_sala', sala_id=sala.id)
    return redirect('home')