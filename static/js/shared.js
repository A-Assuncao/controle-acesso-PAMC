// Funções compartilhadas entre dashboard e testes

// Debounce function para evitar múltiplas chamadas
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// Busca de servidores
const buscarServidorDebounced = debounce((query, urlBusca) => {
    console.log('====== INÍCIO: buscarServidorDebounced() ======');
    console.log('Iniciando busca:', { query, urlBusca });
    
    if (query.length >= 3) {
        const url = urlBusca + `?query=${encodeURIComponent(query)}`;
        console.log('URL da busca completa:', url);
        
        fetch(url)
            .then(response => {
                console.log('Status da resposta:', response.status);
                console.log('Headers da resposta:', Object.fromEntries(response.headers.entries()));
                
                if (!response.ok) {
                    console.error('Resposta não OK:', response.status, response.statusText);
                    throw new Error('Erro na busca: ' + response.status + ' ' + response.statusText);
                }
                
                return response.text().then(text => {
                    console.log('Texto da resposta:', text.substring(0, 500) + (text.length > 500 ? '...' : ''));
                    try {
                        return JSON.parse(text);
                    } catch (e) {
                        console.error('Erro ao fazer parse do JSON:', e);
                        console.error('Texto recebido (primeiros 500 caracteres):', text.substring(0, 500));
                        throw new Error('Resposta não é um JSON válido: ' + e.message);
                    }
                });
            })
            .then(data => {
                console.log('Dados recebidos (estrutura):', Object.keys(data));
                console.log('Status da busca:', data.status);
                console.log('Quantidade de resultados:', data.resultados ? data.resultados.length : 'N/A');
                
                const resultados = document.getElementById('resultados-busca');
                resultados.innerHTML = '';
                
                if (data.status === 'success' && data.resultados && data.resultados.length > 0) {
                    console.log('Processando resultados da busca');
                    
                    data.resultados.forEach((servidor, index) => {
                        console.log(`Processando servidor #${index + 1}:`, servidor.id, servidor.nome);
                        
                        const item = document.createElement('a');
                        item.href = '#';
                        item.className = 'list-group-item list-group-item-action';
                        item.innerHTML = `
                            <div class="d-flex justify-content-between">
                                <div>
                                    <h6 class="mb-1">${servidor.nome}</h6>
                                    <small class="text-muted">${servidor.documento}</small>
                                </div>
                                <div class="text-end">
                                    <small class="d-block">${servidor.setor || '-'}</small>
                                    <small class="d-block text-muted">${servidor.veiculo || '-'}</small>
                                </div>
                            </div>
                        `;
                        item.onclick = function(e) {
                            e.preventDefault();
                            console.log('Servidor selecionado:', servidor);
                            selecionarServidor(servidor);
                        };
                        resultados.appendChild(item);
                    });
                    resultados.style.display = 'block';
                    console.log('Lista de resultados exibida');
                } else {
                    console.log('Nenhum servidor encontrado ou estrutura incorreta');
                    console.log('Status da busca:', data.status);
                    console.log('Dados de resultados:', data.resultados);
                    
                    resultados.innerHTML = '<div class="list-group-item">Nenhum servidor encontrado</div>';
                    resultados.style.display = 'block';
                }
                console.log('====== FIM: buscarServidorDebounced() ======');
            })
            .catch(error => {
                console.error('Erro ao buscar servidores:', error);
                console.error('Stack trace:', error.stack);
                
                const resultados = document.getElementById('resultados-busca');
                resultados.innerHTML = '<div class="list-group-item text-danger">Erro ao buscar servidores</div>';
                resultados.style.display = 'block';
                console.log('====== FIM COM ERRO: buscarServidorDebounced() ======');
            });
    } else {
        document.getElementById('resultados-busca').style.display = 'none';
        console.log('Query muito curta, ocultando resultados');
        console.log('====== FIM (query curta): buscarServidorDebounced() ======');
    }
}, 300);

// Função de busca que será chamada pelos eventos
function buscarServidor(query, urlBusca) {
    buscarServidorDebounced(query, urlBusca);
}

// Atualiza a planilha de registros
function atualizarPlanilha() {
    const url = window.location.pathname.includes('treinamento') ? '/treinamento/registros/' : '/registros-plantao/';
    
    fetch(url)
        .then(response => response.json())
        .then(data => {
            const tbody = document.querySelector('#planilha-registros tbody');
            tbody.innerHTML = '';
            
            if (data.status === 'success' && data.data) {
                data.data.forEach((registro, index) => {
                    const tr = document.createElement('tr');
                    tr.innerHTML = `
                        <td>${index + 1}</td>
                        <td>${registro.servidor_nome}</td>
                        <td>${registro.servidor_documento}</td>
                        <td>${registro.setor}</td>
                        <td>${registro.veiculo}</td>
                        <td>${registro.isv ? 'Sim' : 'Não'}</td>
                        <td>${registro.hora_entrada || '-'}</td>
                        <td>${registro.hora_saida || '-'}</td>
                        <td>
                            <div class="btn-group">
                                <button type="button" class="btn btn-sm btn-secondary dropdown-toggle" data-bs-toggle="dropdown">
                                    Ações
                                </button>
                                <ul class="dropdown-menu">
                                    ${registro.saida_pendente ? `
                                        <li><a class="dropdown-item" href="#" onclick="registrarSaida(${registro.id})">Registrar Saída</a></li>
                                    ` : ''}
                                    <li><a class="dropdown-item" href="#" onclick="editarRegistro(${registro.id})">Editar</a></li>
                                    <li><a class="dropdown-item" href="#" onclick="excluirRegistro(${registro.id})">Excluir</a></li>
                                </ul>
                            </div>
                        </td>
                    `;
                    tbody.appendChild(tr);
                });
            }
            
            // Atualiza os contadores
            atualizarContadores();
        })
        .catch(error => console.error('Erro ao atualizar planilha:', error));
}

// Atualiza os contadores do dashboard
function atualizarContadores() {
    const url = window.location.pathname.includes('treinamento') ? '/treinamento/registros/' : '/registros-plantao/';
    
    fetch(url)
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success' && data.data) {
                const entradas = data.data.filter(r => r.tipo_acesso === 'ENTRADA').length;
                const saidas = data.data.filter(r => r.hora_saida && r.hora_saida !== '-').length;
                const pendentes = data.data.filter(r => r.saida_pendente).length;
                
                document.getElementById('total-entradas').textContent = entradas;
                document.getElementById('total-saidas').textContent = saidas;
                document.getElementById('total-pendentes').textContent = pendentes;
            }
        })
        .catch(error => console.error('Erro ao atualizar contadores:', error));
}

// Seleção de servidor
function selecionarServidor(servidor) {
    console.log('Servidor selecionado:', servidor); // Debug
    
    // Limpa o formulário antes de preencher
    const form = document.getElementById('registroForm');
    if (form) form.reset();
    
    // Preenche os campos do servidor
    document.getElementById('servidor_id').value = servidor.id;
    document.getElementById('servidor_nome').value = servidor.nome;
    document.getElementById('resultados-busca').style.display = 'none';
    document.getElementById('busca-servidor').value = servidor.nome;
    
    // Reseta o tipo de acesso para ENTRADA
    document.getElementById('tipo_acesso').value = 'ENTRADA';
    selecionarTipoAcesso('ENTRADA');
    
    // Abre o modal de registro
    const modalElement = document.getElementById('registroModal');
    if (modalElement) {
        const modal = new bootstrap.Modal(modalElement);
        modal.show();
        
        // Adiciona listener para quando o modal for fechado
        modalElement.addEventListener('hidden.bs.modal', function () {
            form.reset();
            document.getElementById('busca-servidor').value = '';
            carregarRegistros();
        }, { once: true });
    }
}

// Funções de modal
function abrirModalRegistro() {
    const modalElement = document.getElementById('registroModal');
    if (!modalElement) return;
    
    const modal = new bootstrap.Modal(modalElement);
    const form = document.getElementById('registroForm');
    
    if (!form) return;
    
    form.reset();
    
    modalElement.addEventListener('hidden.bs.modal', function () {
        form.reset();
        document.getElementById('busca-servidor').value = '';
        carregarRegistros();
    }, { once: true });
    
    modal.show();
}

function abrirModalSaidaDefinitiva() {
    const modalElement = document.getElementById('saidaDefinitivaModal');
    if (!modalElement) {
        console.error('Modal de saída definitiva não encontrado');
        return;
    }
    
    const modal = new bootstrap.Modal(modalElement);
    modal.show();
}

function confirmarLimparPlanilha() {
    const modal = new bootstrap.Modal(document.getElementById('limparPlanilhaModal'));
    modal.show();
}

// Seleciona o tipo de acesso
function selecionarTipoAcesso(tipo) {
    console.log('Tipo de acesso selecionado:', tipo); // Debug
    
    // Atualiza o campo hidden
    document.getElementById('tipo_acesso').value = tipo;
    
    // Atualiza os botões
    const btnEntrada = document.querySelector('button[onclick="selecionarTipoAcesso(\'ENTRADA\')"]');
    const btnSaida = document.querySelector('button[onclick="selecionarTipoAcesso(\'SAIDA\')"]');
    
    if (btnEntrada && btnSaida) {
        if (tipo === 'ENTRADA') {
            btnEntrada.classList.remove('btn-outline-success');
            btnEntrada.classList.add('btn-success');
            btnSaida.classList.remove('btn-danger');
            btnSaida.classList.add('btn-outline-danger');
        } else {
            btnEntrada.classList.remove('btn-success');
            btnEntrada.classList.add('btn-outline-success');
            btnSaida.classList.remove('btn-outline-danger');
            btnSaida.classList.add('btn-danger');
        }
    }
}

/**
 * Configura navegação por teclado na interface
 */
function setupKeyboardNavigation() {
    document.addEventListener('keydown', function(e) {
        // F2 - Abre modal de registro rápido
        if (e.key === 'F2') {
            e.preventDefault();
            const servidorId = document.getElementById('servidor_id');
            if (servidorId && servidorId.value) {
                abrirModalRegistro();
            } else {
                document.getElementById('busca-servidor').focus();
            }
        }
        
        // F5 - Atualiza a lista de registros
        if (e.key === 'F5') {
            e.preventDefault();
            carregarRegistros();
        }
        
        // CTRL+F - Foca na busca
        if (e.key === 'f' && e.ctrlKey) {
            e.preventDefault();
            document.getElementById('busca-servidor').focus();
        }
    });
}

// Carrega os registros da planilha com debounce
const carregarRegistrosDebounced = debounce(() => {
    const url = window.location.pathname.includes('treinamento') ? '/treinamento/registros/' : '/registros-plantao/';
    console.log('Carregando registros de:', url);
    
    fetch(url)
        .then(response => {
            console.log('Status da resposta:', response.status);
            if (!response.ok) {
                throw new Error('Erro ao carregar registros');
            }
            return response.json();
        })
        .then(data => {
            console.log('Dados recebidos:', data);
            
            const tbody = document.querySelector('table tbody');
            if (!tbody) return;
            
            tbody.innerHTML = '';
            
            if (data.status === 'success' && data.registros && data.registros.length > 0) {
                // Função para converter data no formato dd/mm/aaaa para um objeto Date
                function parseDataBrasileira(dataStr, horaStr) {
                    if (!dataStr) return null;
                    const partes = dataStr.split('/');
                    const dataFormatada = `${partes[2]}-${partes[1]}-${partes[0]}`;
                    return new Date(`${dataFormatada}T${horaStr || '00:00'}`);
                }
                
                // Ordena os registros por data e hora (mais antigos primeiro)
                const registrosOrdenados = data.registros.sort((a, b) => {
                    // Se ambos têm hora_entrada, comparamos por ela
                    const dataEntradaA = parseDataBrasileira(a.data_entrada || a.data, a.hora_entrada);
                    const dataEntradaB = parseDataBrasileira(b.data_entrada || b.data, b.hora_entrada);
                    
                    if (dataEntradaA && dataEntradaB) {
                        return dataEntradaA - dataEntradaB;
                    }
                    
                    // Se um tem data de entrada e o outro não, o que tem vem primeiro
                    if (dataEntradaA && !dataEntradaB) return -1;
                    if (!dataEntradaA && dataEntradaB) return 1;
                    
                    // Se nenhum tem data de entrada, comparamos por data de saída
                    const dataSaidaA = parseDataBrasileira(a.data_saida, a.hora_saida);
                    const dataSaidaB = parseDataBrasileira(b.data_saida, b.hora_saida);
                    
                    if (dataSaidaA && dataSaidaB) {
                        return dataSaidaA - dataSaidaB;
                    }
                    
                    // Se chegou aqui, não temos como comparar, retorna 0
                    return 0;
                });
                
                registrosOrdenados.forEach((registro, index) => {
                    const tr = document.createElement('tr');
                    
                    // Prepara o texto de entrada e saída
                    const dataHoraEntrada = registro.data_entrada && registro.hora_entrada 
                        ? `${registro.data_entrada} ${registro.hora_entrada}` 
                        : '-';
                    
                    const dataHoraSaida = registro.data_saida && registro.hora_saida 
                        ? `${registro.data_saida} ${registro.hora_saida}` 
                        : '-';
                    
                    tr.innerHTML = `
                        <td>${index + 1}</td>
                        <td>${registro.servidor_nome || '-'}</td>
                        <td>${registro.servidor_documento || '-'}</td>
                        <td>${registro.setor || '-'}</td>
                        <td>${registro.veiculo || '-'}</td>
                        <td>${registro.isv ? 'Sim' : 'Não'}</td>
                        <td>${dataHoraEntrada}</td>
                        <td>${dataHoraSaida}</td>
                        <td>
                            <div class="dropdown">
                                <button class="btn btn-sm btn-secondary dropdown-toggle" type="button" data-bs-toggle="dropdown">
                                    Ações
                                </button>
                                <ul class="dropdown-menu">
                                    ${registro.saida_pendente ? `
                                        <li>
                                            <a class="dropdown-item" href="#" onclick="registrarSaida(${registro.id})">
                                                <i class="bi bi-box-arrow-right me-2"></i>
                                                Registrar Saída
                                            </a>
                                        </li>
                                    ` : ''}
                                    <li>
                                        <a class="dropdown-item" href="#" onclick="editarRegistro(${registro.id})">
                                            <i class="bi bi-pencil me-2"></i>
                                            Editar
                                        </a>
                                    </li>
                                    <li>
                                        <a class="dropdown-item" href="#" onclick="excluirRegistro(${registro.id})">
                                            <i class="bi bi-trash me-2"></i>
                                            Excluir
                                        </a>
                                    </li>
                                </ul>
                            </div>
                        </td>
                    `;
                    tbody.appendChild(tr);
                });
            } else {
                tbody.innerHTML = `
                    <tr>
                        <td colspan="10" class="text-center">
                            <div class="alert alert-info mb-0">
                                <i class="bi bi-info-circle me-2"></i>
                                Nenhum registro encontrado
                            </div>
                        </td>
                    </tr>
                `;
            }
            
            // Atualiza os contadores
            document.getElementById('total-entradas').textContent = data.total_entradas || '0';
            document.getElementById('total-saidas').textContent = data.total_saidas || '0';
            document.getElementById('total-pendentes').textContent = data.total_pendentes || '0';
        })
        .catch(error => {
            console.error('Erro ao carregar registros:', error);
            const tbody = document.querySelector('table tbody');
            if (tbody) {
                tbody.innerHTML = `
                    <tr>
                        <td colspan="10" class="text-center">
                            <div class="alert alert-danger mb-0">
                                <i class="bi bi-exclamation-triangle me-2"></i>
                                Erro ao carregar registros: ${error.message}
                            </div>
                        </td>
                    </tr>
                `;
            }
        });
}, 300);

// Função de carregamento que será chamada pelos eventos
function carregarRegistros() {
    console.log('====== INÍCIO: carregarRegistros() ======');
    console.log('Chamando carregarRegistros...'); // Debug
    
    const url = window.location.pathname.includes('treinamento') ? '/treinamento/registros/' : '/registros-plantao/';
    console.log('URL para carregar registros:', url); // Debug
    
    fetch(url)
        .then(response => {
            console.log('Status da resposta:', response.status); // Debug
            console.log('Headers da resposta:', Object.fromEntries(response.headers.entries()));
            
            if (!response.ok) {
                console.error('Resposta não OK:', response.status, response.statusText);
                throw new Error('Erro ao carregar registros: ' + response.status + ' ' + response.statusText);
            }
            return response.text().then(text => {
                console.log('Texto da resposta:', text.substring(0, 500) + (text.length > 500 ? '...' : ''));
                try {
                    return JSON.parse(text);
                } catch (e) {
                    console.error('Erro ao fazer parse do JSON:', e);
                    console.error('Texto recebido (primeiros 500 caracteres):', text.substring(0, 500));
                    throw new Error('Resposta não é um JSON válido: ' + e.message);
                }
            });
        })
        .then(data => {
            console.log('Dados recebidos (estrutura):', Object.keys(data)); // Debug
            console.log('Status:', data.status);
            console.log('Total de registros:', data.registros ? data.registros.length : 'N/A');
            
            const tbody = document.querySelector('table tbody');
            if (!tbody) {
                console.error('Tabela não encontrada no DOM');
                return;
            }
            
            tbody.innerHTML = '';
            
            // Referência ao elemento de instrução sobre clique direito
            const instrucoesCliqueDir = document.querySelector('.mt-3 small.text-muted');
            
            if (data.status === 'success' && data.registros && data.registros.length > 0) {
                console.log(`Renderizando ${data.registros.length} registros`);
                
                // Mostra as instruções de clique direito quando há registros
                if (instrucoesCliqueDir) {
                    instrucoesCliqueDir.style.display = 'inline-block';
                }
                
                // Função para converter data no formato dd/mm/aaaa para um objeto Date
                function parseDataBrasileira(dataStr, horaStr) {
                    if (!dataStr) return null;
                    console.log('Parseando data/hora:', dataStr, horaStr);
                    // Split da data dd/mm/aaaa para [dd, mm, aaaa]
                    const partes = dataStr.split('/');
                    // Cria string no formato aaaa-mm-dd para o construtor Date
                    const dataFormatada = `${partes[2]}-${partes[1]}-${partes[0]}`;
                    return new Date(`${dataFormatada}T${horaStr || '00:00'}`);
                }
                
                // Ordena os registros por data e hora (mais antigos primeiro)
                const registrosOrdenados = data.registros.sort((a, b) => {
                    // Se ambos têm hora_entrada, comparamos por ela
                    const dataEntradaA = parseDataBrasileira(a.data_entrada || a.data, a.hora_entrada);
                    const dataEntradaB = parseDataBrasileira(b.data_entrada || b.data, b.hora_entrada);
                    
                    if (dataEntradaA && dataEntradaB) {
                        return dataEntradaA - dataEntradaB;
                    }
                    
                    // Se um tem data de entrada e o outro não, o que tem vem primeiro
                    if (dataEntradaA && !dataEntradaB) return -1;
                    if (!dataEntradaA && dataEntradaB) return 1;
                    
                    // Se nenhum tem data de entrada, comparamos por data de saída
                    const dataSaidaA = parseDataBrasileira(a.data_saida, a.hora_saida);
                    const dataSaidaB = parseDataBrasileira(b.data_saida, b.hora_saida);
                    
                    if (dataSaidaA && dataSaidaB) {
                        return dataSaidaA - dataSaidaB;
                    }
                    
                    // Se chegou aqui, não temos como comparar, retorna 0
                    return 0;
                });
                
                registrosOrdenados.forEach((registro, index) => {
                    console.log(`Processando registro #${index + 1}:`, registro.id, registro.servidor_nome);
                    
                    const tr = document.createElement('tr');
                    tr.dataset.id = registro.id;
                    
                    // Prepara o texto de entrada e saída
                    const dataHoraEntrada = registro.data_entrada && registro.hora_entrada 
                        ? `${registro.data_entrada} ${registro.hora_entrada}` 
                        : '-';
                    
                    const dataHoraSaida = registro.data_saida && registro.hora_saida 
                        ? `${registro.data_saida} ${registro.hora_saida}` 
                        : '-';
                    
                    tr.innerHTML = `
                        <td>${index + 1}</td>
                        <td>${registro.servidor_nome || '-'}</td>
                        <td>${registro.servidor_documento || '-'}</td>
                        <td>${registro.setor || '-'}</td>
                        <td>${registro.veiculo || '-'}</td>
                        <td>${registro.isv ? 'Sim' : 'Não'}</td>
                        <td>${dataHoraEntrada}</td>
                        <td>${dataHoraSaida}</td>
                    `;
                    
                    // Adiciona evento de clique direito para menu de contexto
                    tr.addEventListener('contextmenu', function(e) {
                        e.preventDefault();
                        showContextMenu(e, registro);
                    });
                    
                    tbody.appendChild(tr);
                });
            } else {
                console.log('Nenhum registro encontrado ou estrutura incorreta');
                console.log('Status:', data.status);
                console.log('Dados de registros:', data.registros);
                
                // Oculta as instruções de clique direito quando não há registros
                if (instrucoesCliqueDir) {
                    instrucoesCliqueDir.style.display = 'none';
                }
                
                tbody.innerHTML = `
                    <tr>
                        <td colspan="8" class="text-center">
                            <div class="alert alert-info mb-0">
                                <i class="bi bi-info-circle me-2"></i>
                                Nenhum registro encontrado
                            </div>
                        </td>
                    </tr>
                `;
            }
            
            // Atualiza os contadores
            document.getElementById('total-entradas').textContent = data.total_entradas || '0';
            document.getElementById('total-saidas').textContent = data.total_saidas || '0';
            document.getElementById('total-pendentes').textContent = data.total_pendentes || '0';
            
            console.log('Contadores atualizados');
            console.log('====== FIM: carregarRegistros() ======');
        })
        .catch(error => {
            console.error('Erro ao carregar registros:', error);
            console.error('Stack trace:', error.stack);
            
            const tbody = document.querySelector('table tbody');
            
            // Referência ao elemento de instrução sobre clique direito
            const instrucoesCliqueDir = document.querySelector('.mt-3 small.text-muted');
            
            // Oculta as instruções de clique direito em caso de erro
            if (instrucoesCliqueDir) {
                instrucoesCliqueDir.style.display = 'none';
            }
            
            if (tbody) {
                tbody.innerHTML = `
                    <tr>
                        <td colspan="8" class="text-center">
                            <div class="alert alert-danger mb-0">
                                <i class="bi bi-exclamation-triangle me-2"></i>
                                Erro ao carregar registros: ${error.message}
                            </div>
                        </td>
                    </tr>
                `;
            }
            console.log('====== FIM COM ERRO: carregarRegistros() ======');
        });
}

// Função para exibir o menu de contexto
function showContextMenu(e, registro) {
    const contextMenu = document.getElementById('contextMenu');
    const menuEditar = document.getElementById('menuEditar');
    const menuExcluir = document.getElementById('menuExcluir');
    const menuRegistrarSaida = document.getElementById('menuRegistrarSaida');
    
    // Primeiro, fecha qualquer menu já aberto
    contextMenu.classList.remove('show');
    
    // Remove eventos de clique antigos para evitar múltiplos handlers
    document.removeEventListener('click', window.closeContextMenuHandler);
    
    // Configura as ações do menu
    menuEditar.onclick = function() {
        contextMenu.classList.remove('show');
        editarRegistro(registro.id);
    };
    
    menuExcluir.onclick = function() {
        contextMenu.classList.remove('show');
        excluirRegistro(registro.id);
    };
    
    // Mostra/esconde a opção de registrar saída com base no status
    if (registro.saida_pendente) {
        menuRegistrarSaida.style.display = 'block';
        menuRegistrarSaida.onclick = function() {
            contextMenu.classList.remove('show');
            registrarSaida(registro.id);
        };
    } else {
        menuRegistrarSaida.style.display = 'none';
    }
    
    // Posiciona e exibe o menu
    // Calcula a posição para manter o menu dentro da janela
    let x = e.pageX;
    let y = e.pageY;
    
    // Calcula as dimensões
    const menuWidth = contextMenu.offsetWidth || 150;
    const menuHeight = contextMenu.offsetHeight || 120;
    const windowWidth = window.innerWidth;
    const windowHeight = window.innerHeight;
    
    // Ajusta a posição se necessário
    if (x + menuWidth > windowWidth) {
        x = windowWidth - menuWidth - 5;
    }
    
    if (y + menuHeight > windowHeight) {
        y = windowHeight - menuHeight - 5;
    }
    
    // Define a posição final
    contextMenu.style.top = `${y}px`;
    contextMenu.style.left = `${x}px`;
    contextMenu.classList.add('show');
    
    // Função para fechar o menu ao clicar em qualquer lugar
    window.closeContextMenuHandler = function(evt) {
        // Se clicou fora do menu, fecha
        if (!contextMenu.contains(evt.target)) {
            contextMenu.classList.remove('show');
            document.removeEventListener('click', window.closeContextMenuHandler);
        }
    };
    
    // Adiciona o listener com um pequeno atraso para evitar que o clique atual o feche
    setTimeout(() => {
        document.addEventListener('click', window.closeContextMenuHandler);
    }, 100);
    
    // Fecha o menu ao pressionar Escape
    document.addEventListener('keydown', function escHandler(evt) {
        if (evt.key === 'Escape') {
            contextMenu.classList.remove('show');
            document.removeEventListener('keydown', escHandler);
        }
    });
}

// Registra a saída de um servidor
function registrarSaida(registroId) {
    console.log('Registrando saída para o registro:', registroId); // Debug
    
    Swal.fire({
        title: 'Confirmar Saída',
        text: 'Deseja registrar a saída deste servidor?',
        icon: 'question',
        showCancelButton: true,
        confirmButtonText: 'Sim, registrar',
        cancelButtonText: 'Cancelar'
    }).then((result) => {
        if (result.isConfirmed) {
            const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;
            
            fetch(`/treinamento/registro/${registroId}/saida/`, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': csrfToken
                }
            })
            .then(response => {
                console.log('Status da resposta:', response.status); // Debug
                return response.json();
            })
            .then(data => {
                console.log('Resposta recebida:', data); // Debug
                if (data.status === 'success') {
                    Swal.fire({
                        icon: 'success',
                        title: 'Sucesso!',
                        text: 'Saída registrada com sucesso!',
                        timer: 2000,
                        showConfirmButton: false
                    });
                    carregarRegistros();
                } else {
                    throw new Error(data.message || 'Erro ao registrar saída');
                }
            })
            .catch(error => {
                console.error('Erro ao registrar saída:', error);
                Swal.fire({
                    icon: 'error',
                    title: 'Erro!',
                    text: error.message || 'Erro ao registrar saída'
                });
            });
        }
    });
}

// Edita um registro
function editarRegistro(registroId) {
    console.log('Editando registro:', registroId);

    // Obtém o token CSRF
    const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;
    
    // Define a URL baseada no ambiente (treinamento ou produção)
    const url = window.location.pathname.includes('treinamento') 
        ? `/treinamento/registro/${registroId}/detalhe/` 
        : `/registro/${registroId}/`;  // URL corrigida para '/registro/{id}/'
    
    console.log('URL para obter detalhes:', url);
    
    // Mostra um indicador de carregamento
    Swal.fire({
        title: 'Carregando...',
        text: 'Buscando dados do registro',
        allowOutsideClick: false,
        didOpen: () => {
            Swal.showLoading();
        }
    });
    
    fetch(url)
        .then(response => {
            console.log('Status da resposta:', response.status, response.statusText);
            
            if (!response.ok) {
                return response.text().then(text => {
                    console.error('Resposta de erro:', text);
                    try {
                        // Tenta fazer o parse como JSON
                        const data = JSON.parse(text);
                        throw new Error(data.message || 'Erro ao carregar os dados do registro');
                    } catch (e) {
                        throw new Error('Erro ao carregar os dados do registro');
                    }
                });
            }
            
            return response.json();
        })
        .then(data => {
            console.log('Dados do registro recebidos do servidor:', data);
            Swal.close(); // Fecha o indicador de carregamento
            
            // Função para converter data de DD/MM/AAAA para AAAA-MM-DD (formato aceito pelo input type=date)
            function converterDataParaHtml(dataStr) {
                if (!dataStr) return '';
                
                console.log(`Convertendo data '${dataStr}' para formato HTML`);
                const partes = dataStr.split('/');
                if (partes.length !== 3) {
                    console.warn(`Formato de data inválido: ${dataStr}`);
                    return '';
                }
                const resultado = `${partes[2]}-${partes[1]}-${partes[0]}`;
                console.log(`Data convertida para HTML: ${resultado}`);
                return resultado;
            }
            
            // Converte as datas para o formato HTML
            const dataEntradaHtml = converterDataParaHtml(data.data_entrada);
            const dataSaidaHtml = data.data_saida ? converterDataParaHtml(data.data_saida) : '';
            
            // Log completo de todos os dados e conversões
            console.log('====== DADOS PARA O MODAL DE EDIÇÃO ======');
            console.log('Datas no formato brasileiro (dd/mm/aaaa):');
            console.log(`- Data Entrada: ${data.data_entrada || 'N/A'}`);
            console.log(`- Data Saída: ${data.data_saida || 'N/A'}`);
            console.log('Horas (hh:mm):');
            console.log(`- Hora Entrada: ${data.hora_entrada || 'N/A'}`);
            console.log(`- Hora Saída: ${data.hora_saida || 'N/A'}`);
            console.log('Datas convertidas para formato HTML (yyyy-mm-dd):');
            console.log(`- Data Entrada HTML: ${dataEntradaHtml}`);
            console.log(`- Data Saída HTML: ${dataSaidaHtml}`);
            console.log('======================================');
            
            // Constrói o HTML do formulário de edição
            Swal.fire({
                title: 'Editar Registro',
                html: `
                    <form id="editarForm" class="text-start">
                        <div class="mb-3">
                            <label class="form-label">Servidor</label>
                            <input type="text" class="form-control" value="${data.servidor?.nome || ''}" readonly>
                        </div>
                        
                        <div class="row">
                            <div class="col-md-6 border-end pe-3">
                                <h6 class="mb-3 text-primary">Entrada</h6>
                                <div class="mb-3">
                                    <label class="form-label">Data</label>
                                    <input type="date" name="data_entrada" class="form-control" value="${dataEntradaHtml}" required>
                                </div>
                                <div class="mb-3">
                                    <label class="form-label">Hora</label>
                                    <input type="time" name="hora_entrada" class="form-control" value="${data.hora_entrada || ''}" required>
                                </div>
                            </div>
                            
                            <div class="col-md-6 ps-3">
                                <h6 class="mb-3 text-danger">Saída</h6>
                                <div class="mb-3">
                                    <label class="form-label">Data</label>
                                    <input type="date" name="data_saida" class="form-control" value="${dataSaidaHtml}">
                                </div>
                                <div class="mb-3">
                                    <label class="form-label">Hora</label>
                                    <input type="time" name="hora_saida" class="form-control" value="${data.hora_saida || ''}">
                                </div>
                            </div>
                        </div>
                        
                        <div class="mb-3 mt-3">
                            <div class="form-check">
                                <input type="checkbox" class="form-check-input" id="isv" name="isv" ${data.isv ? 'checked' : ''}>
                                <label class="form-check-label" for="isv">É Serviço Voluntário?</label>
                            </div>
                        </div>
                        <!-- Campo oculto para justificativa -->
                        <input type="hidden" name="justificativa" value="Treinamento">
                    </form>
                `,
                showCancelButton: true,
                confirmButtonText: 'Salvar',
                cancelButtonText: 'Cancelar',
                didOpen: () => {
                    // Configura validação quando o modal abre
                    const form = document.getElementById('editarForm');
                    const dataEntrada = form.querySelector('[name="data_entrada"]');
                    const horaEntrada = form.querySelector('[name="hora_entrada"]');
                    const dataSaida = form.querySelector('[name="data_saida"]');
                    const horaSaida = form.querySelector('[name="hora_saida"]');
                    
                    console.log('Valores preenchidos no formulário:');
                    console.log(`- Data Entrada: ${dataEntrada.value}`);
                    console.log(`- Hora Entrada: ${horaEntrada.value}`);
                    console.log(`- Data Saída: ${dataSaida.value}`);
                    console.log(`- Hora Saída: ${horaSaida.value}`);
                    
                    // Entrada é sempre obrigatória
                    dataEntrada.required = true;
                    horaEntrada.required = true;
                    
                    // Adiciona listeners para validar os campos de saída
                    // Se um dos campos de saída for preenchido, o outro também deve ser
                    dataSaida.addEventListener('input', validarCamposSaida);
                    horaSaida.addEventListener('input', validarCamposSaida);
                    
                    function validarCamposSaida() {
                        if (dataSaida.value && !horaSaida.value) {
                            horaSaida.setCustomValidity('Se você informar a data de saída, também precisa informar a hora');
                            horaSaida.required = true;
                        } else if (!dataSaida.value && horaSaida.value) {
                            dataSaida.setCustomValidity('Se você informar a hora de saída, também precisa informar a data');
                            dataSaida.required = true;
                        } else {
                            dataSaida.setCustomValidity('');
                            horaSaida.setCustomValidity('');
                            
                            // Se ambos estão preenchidos ou ambos estão vazios, não são obrigatórios entre si
                            const ambosPreenchidos = dataSaida.value && horaSaida.value;
                            const ambosVazios = !dataSaida.value && !horaSaida.value;
                            
                            if (ambosPreenchidos || ambosVazios) {
                                dataSaida.required = ambosPreenchidos;
                                horaSaida.required = ambosPreenchidos;
                            }
                        }
                    }
                    
                    // Executa a validação inicial
                    validarCamposSaida();
                },
                preConfirm: () => {
                    const form = document.getElementById('editarForm');
                    const formData = new FormData(form);
                    
                    // Obtém os valores do formulário para debugging
                    const dataEntrada = formData.get('data_entrada');
                    const horaEntrada = formData.get('hora_entrada');
                    const dataSaida = formData.get('data_saida');
                    const horaSaida = formData.get('hora_saida');
                    const isv = formData.get('isv') === 'on';
                    
                    console.log('===== DADOS QUE SERÃO ENVIADOS AO SERVIDOR =====');
                    console.log(`- Data Entrada: ${dataEntrada}`);
                    console.log(`- Hora Entrada: ${horaEntrada}`);
                    console.log(`- Data Saída: ${dataSaida || '<vazio>'}`);
                    console.log(`- Hora Saída: ${horaSaida || '<vazio>'}`);
                    console.log(`- ISV: ${isv}`);
                    console.log('===============================================');
                    
                    // Validações adicionais antes de enviar
                    if (!dataEntrada || !horaEntrada) {
                        Swal.showValidationMessage('Data e hora de entrada são obrigatórios');
                        return false;
                    }
                    
                    if ((dataSaida && !horaSaida) || (!dataSaida && horaSaida)) {
                        const campoFaltante = !dataSaida ? 'data' : 'hora';
                        Swal.showValidationMessage(`Para registrar uma saída, preencha tanto a data quanto a hora. Campo faltando: ${campoFaltante}`);
                        return false;
                    }
                    
                    const url = window.location.pathname.includes('treinamento') 
                        ? `/treinamento/registro/${registroId}/editar/` 
                        : `/registro/${registroId}/editar/`;
                    
                    console.log('Enviando dados para:', url);
                    
                    return fetch(url, {
                        method: 'POST',
                        headers: {
                            'X-CSRFToken': csrfToken
                        },
                        body: formData
                    })
                    .then(response => {
                        console.log('Status da resposta da edição:', response.status);
                        return response.text().then(text => {
                            console.log('Resposta bruta do servidor:', text);
                            try {
                                return text ? JSON.parse(text) : {};
                            } catch (e) {
                                console.error('Erro ao fazer parse da resposta:', text);
                                throw new Error('A resposta do servidor não é um JSON válido');
                            }
                        });
                    })
                    .then(data => {
                        console.log('Resposta processada da edição:', data);
                        if (data.status === 'error') {
                            throw new Error(data.message || 'Erro ao atualizar o registro');
                        }
                        return data;
                    })
                    .catch(error => {
                        console.error('Erro ao editar registro:', error);
                        Swal.showValidationMessage(error.message || 'Erro ao atualizar o registro');
                        return false;
                    });
                }
            }).then((result) => {
                if (result.isConfirmed) {
                    Swal.fire({
                        icon: 'success',
                        title: 'Sucesso!',
                        text: 'Registro atualizado com sucesso!',
                        timer: 2000,
                        showConfirmButton: false
                    });
                    
                    // Recarrega a planilha
                    carregarRegistros();
                }
            });
        })
        .catch(error => {
            console.error('Erro ao carregar registro:', error);
            Swal.close(); // Fecha o indicador de carregamento em caso de erro
            Swal.fire({
                icon: 'error',
                title: 'Erro!',
                text: error.message || 'Erro ao carregar os dados do registro'
            });
        });
}

// Exclui um registro
function excluirRegistro(registroId) {
    console.log('Excluindo registro:', registroId); // Debug
    
    Swal.fire({
        title: 'Excluir Registro',
        text: 'Tem certeza que deseja excluir este registro?',
        icon: 'warning',
        input: 'textarea',
        inputLabel: 'Justificativa*',
        inputPlaceholder: 'Digite a justificativa para a exclusão...',
        inputAttributes: {
            required: 'required'
        },
        showCancelButton: true,
        confirmButtonText: 'Sim, excluir',
        cancelButtonText: 'Cancelar',
        preConfirm: (justificativa) => {
            if (!justificativa) {
                Swal.showValidationMessage('A justificativa é obrigatória');
                return false;
            }
            
            const formData = new FormData();
            formData.append('justificativa', justificativa);
            
            const url = window.location.pathname.includes('treinamento') 
                ? `/treinamento/registro/${registroId}/excluir/` 
                : `/registro/${registroId}/excluir/`;
            
            return fetch(url, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value
                },
                body: formData
            })
            .then(response => response.json())
            .then(data => {
                if (data.status === 'error') {
                    throw new Error(data.message);
                }
                return data;
            })
            .catch(error => {
                Swal.showValidationMessage(error.message);
            });
        }
    }).then((result) => {
        if (result.isConfirmed) {
            Swal.fire('Sucesso!', 'Registro excluído com sucesso.', 'success');
            carregarRegistros();
        }
    });
}

function enviarFormulario(form) {
    const formData = new FormData(form);
    const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;
    
    return fetch(form.action, {
        method: 'POST',
        headers: {
            'X-CSRFToken': csrfToken
        },
        body: formData
    });
}

// Função para submeter o formulário sem redirect
function submeterFormulario(e, form) {
    e.preventDefault();
    
    const servidorId = document.getElementById('servidor_id').value;
    if (!servidorId) {
        Swal.fire({
            icon: 'error',
            title: 'Erro!',
            text: 'Por favor, selecione um servidor primeiro.'
        });
        return false;
    }
    
    const formData = new FormData(form);
    const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;
    
    fetch(form.action, {
        method: 'POST',
        headers: {
            'X-CSRFToken': csrfToken
        },
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'success') {
            const modalElement = document.getElementById('registroModal');
            const modal = bootstrap.Modal.getInstance(modalElement);
            modal.hide();
            
            form.reset();
            document.getElementById('busca-servidor').value = '';
            carregarRegistros();
            
            Swal.fire({
                icon: 'success',
                title: 'Sucesso!',
                text: data.message,
                timer: 2000,
                showConfirmButton: false
            });
        } else {
            throw new Error(data.message || 'Erro ao processar a requisição');
        }
    })
    .catch(error => {
        console.error('Erro:', error);
        Swal.fire({
            icon: 'error',
            title: 'Erro!',
            text: error.message
        });
    });
    
    return false;
}

// Função para submeter o formulário de saída definitiva sem redirect
function submeterFormularioSaida(e, form) {
    e.preventDefault();
    
    const nome = document.getElementById('nomePreso').value.trim();
    const numeroDocumento = document.getElementById('numeroDocumentoPreso').value.trim();
    const justificativa = form.querySelector('textarea[name="justificativa"]').value.trim();
    
    if (!nome || !numeroDocumento || !justificativa) {
        Swal.fire({
            icon: 'error',
            title: 'Erro!',
            text: 'Por favor, preencha todos os campos obrigatórios.'
        });
        return false;
    }
    
    const formData = new FormData(form);
    formData.append('setor', justificativa); // A justificativa é armazenada no campo setor
    const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;
    
    fetch(form.action, {
        method: 'POST',
        headers: {
            'X-CSRFToken': csrfToken
        },
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'success') {
            const modalElement = document.getElementById('saidaDefinitivaModal');
            const modal = bootstrap.Modal.getInstance(modalElement);
            modal.hide();
            
            form.reset();
            carregarRegistros();
            
            Swal.fire({
                icon: 'success',
                title: 'Sucesso!',
                text: data.message || 'Saída definitiva registrada com sucesso!',
                timer: 2000,
                showConfirmButton: false
            });
        } else {
            throw new Error(data.message || 'Erro ao registrar saída definitiva');
        }
    })
    .catch(error => {
        console.error('Erro:', error);
        Swal.fire({
            icon: 'error',
            title: 'Erro!',
            text: error.message
        });
    });
    
    return false;
}

// Função para limpar a planilha
function limparPlanilha() {
    console.log('====== INÍCIO: limparPlanilha() ======');
    // Obtém o token CSRF
    const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;
    console.log('Token CSRF obtido:', csrfToken ? 'Sim' : 'Não');
    
    // Determina a URL correta baseada no ambiente
    const url = window.location.pathname.includes('treinamento') 
        ? '/treinamento/limpar-dashboard/' 
        : '/limpar-dashboard/';
    
    console.log('URL para limpar planilha:', url);
    
    // Fecha o modal de confirmação
    const modal = bootstrap.Modal.getInstance(document.getElementById('limparPlanilhaModal'));
    if (modal) {
        console.log('Fechando modal de confirmação');
        modal.hide();
    } else {
        console.log('Modal de confirmação não encontrado');
    }
    
    // Mostra um indicador de carregamento
    console.log('Exibindo indicador de carregamento');
    Swal.fire({
        title: 'Limpando planilha...',
        text: 'Por favor, aguarde.',
        allowOutsideClick: false,
        didOpen: () => {
            Swal.showLoading();
        }
    });
    
    // Envia a requisição
    console.log('Enviando requisição para limpar planilha');
    fetch(url, {
        method: 'POST',
        headers: {
            'X-CSRFToken': csrfToken,
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
    })
    .then(response => {
        console.log('Status da resposta:', response.status);
        console.log('Headers da resposta:', Object.fromEntries(response.headers.entries()));
        
        // Tenta obter o conteúdo da resposta como texto
        return response.text().then(text => {
            console.log('Texto da resposta:', text.substring(0, 500) + (text.length > 500 ? '...' : ''));
            
            try {
                // Tenta fazer o parse do texto como JSON
                const data = text ? JSON.parse(text) : {};
                console.log('Dados processados:', data);
                
                // Se a resposta não foi bem sucedida, lança um erro com a mensagem
                if (!response.ok) {
                    console.error('Resposta não OK:', response.status, response.statusText);
                    throw new Error(data.message || `Erro ao limpar planilha: ${response.status} ${response.statusText}`);
                }
                
                return data;
            } catch (e) {
                console.error('Erro ao processar resposta:', e);
                console.error('Texto recebido (primeiros 500 caracteres):', text.substring(0, 500));
                throw new Error('Erro ao processar resposta do servidor: ' + e.message);
            }
        });
    })
    .then(data => {
        console.log('Resposta processada:', data);
        
        if (data.status === 'success') {
            console.log('Limpeza bem-sucedida, exibindo mensagem de sucesso');
            Swal.fire({
                icon: 'success',
                title: 'Sucesso!',
                text: data.message || 'Planilha limpa com sucesso!',
                timer: 2000,
                showConfirmButton: false
            }).then(() => {
                console.log('Recarregando página');
                window.location.reload();
            });
        } else {
            console.error('Status da resposta não é success:', data.status);
            throw new Error(data.message || 'Erro ao limpar planilha');
        }
        console.log('====== FIM: limparPlanilha() ======');
    })
    .catch(error => {
        console.error('Erro ao limpar planilha:', error);
        console.error('Stack trace:', error.stack);
        
        Swal.fire({
            icon: 'error',
            title: 'Erro!',
            text: error.message || 'Erro ao limpar planilha'
        });
        console.log('====== FIM COM ERRO: limparPlanilha() ======');
    });
}

// Função para exportar Excel
function exportarExcel() {
    console.log('====== INÍCIO: exportarExcel() ======');
    const url = window.location.pathname.includes('treinamento') 
        ? '/treinamento/exportar-excel/' 
        : '/exportar-excel/';
    
    console.log('URL para exportar Excel:', url);
    console.log('Redirecionando para a URL de exportação');
    window.location.href = url;
    console.log('====== FIM: exportarExcel() ======');
}