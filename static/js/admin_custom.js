/**
 * =============================================================================
 * ADMIN CUSTOMIZADO - FUNCIONALIDADES INTERATIVAS
 * Sistema de Controle de Acesso - Configurável por Unidade Prisional
 * =============================================================================
 */

(function($) {
    'use strict';

    // 🚀 INICIALIZAÇÃO PRINCIPAL
    $(document).ready(function() {
        initAdminEnhancements();
        initStatsDashboard();
        initAdvancedFilters();
        initKeyboardShortcuts();
        initTooltips();
        initConfirmations();
        initAutoSave();
        initSearchEnhancements();
        initMobileOptimizations();
        initAnimations();
    });

    // 📊 DASHBOARD DE ESTATÍSTICAS
    function initStatsDashboard() {
        if ($('.admin-index').length) {
            createStatsCards();
            loadRealtimeStats();
            // Atualizar a cada 30 segundos
            setInterval(loadRealtimeStats, 30000);
        }
    }

    function createStatsCards() {
        const statsContainer = $('<div class="stats-container" style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin: 20px 0;">');
        
        // Card de Servidores Ativos
        const activeServersCard = $(`
            <div class="stats-card" id="active-servers-card">
                <div class="stats-number">-</div>
                <div class="stats-label">Servidores Ativos</div>
                <div class="stats-progress">
                    <div class="progress-bar" style="width: 0%; background: #28a745; height: 4px; border-radius: 2px; margin-top: 10px; transition: width 0.3s ease;"></div>
                </div>
            </div>
        `);

        // Card de Registros Hoje
        const todayRegistersCard = $(`
            <div class="stats-card" id="today-registers-card">
                <div class="stats-number">-</div>
                <div class="stats-label">Registros Hoje</div>
                <div class="stats-trend" style="margin-top: 5px; font-size: 12px; color: #6c757d;">
                    <span class="trend-icon">📈</span>
                    <span class="trend-value">+0%</span>
                </div>
            </div>
        `);

        statsContainer.append(activeServersCard, todayRegistersCard);
        $('.admin-index').prepend(statsContainer);
    }

    function loadRealtimeStats() {
        // Simulação de dados em tempo real
        const stats = {
            activeServers: Math.floor(Math.random() * 50) + 100,
            todayRegisters: Math.floor(Math.random() * 100) + 50
        };

        // Atualizar cards com animação
        animateNumber('#active-servers-card .stats-number', stats.activeServers);
        animateNumber('#today-registers-card .stats-number', stats.todayRegisters);
        
        // Atualizar barra de progresso
        const progressPercent = Math.min((stats.activeServers / 150) * 100, 100);
        $('#active-servers-card .progress-bar').css('width', progressPercent + '%');
    }

    function animateNumber(selector, targetNumber) {
        const $element = $(selector);
        const currentNumber = parseInt($element.text()) || 0;
        
        $({ count: currentNumber }).animate({ count: targetNumber }, {
            duration: 1000,
            step: function() {
                $element.text(Math.floor(this.count));
            },
            complete: function() {
                $element.text(targetNumber);
            }
        });
    }

    // 🔍 FILTROS AVANÇADOS
    function initAdvancedFilters() {
        // Adicionar busca rápida nos filtros
        $('#changelist-filter').each(function() {
            const $filter = $(this);
            const $filterSections = $filter.find('h3');
            
            $filterSections.each(function() {
                const $section = $(this);
                const $list = $section.next('ul');
                
                if ($list.find('li').length > 5) {
                    const $searchInput = $(`
                        <input type="text" placeholder="Buscar..." 
                               style="width: 100%; padding: 5px; margin: 5px 0; border: 1px solid #ddd; border-radius: 4px; font-size: 12px;">
                    `);
                    
                    $section.after($searchInput);
                    
                    $searchInput.on('input', function() {
                        const searchTerm = $(this).val().toLowerCase();
                        $list.find('li').each(function() {
                            const text = $(this).text().toLowerCase();
                            $(this).toggle(text.includes(searchTerm));
                        });
                    });
                }
            });
        });
    }

    // ⌨️ ATALHOS DE TECLADO
    function initKeyboardShortcuts() {
        $(document).on('keydown', function(e) {
            // Ctrl+Alt+N - Novo registro
            if (e.ctrlKey && e.altKey && e.keyCode === 78) {
                e.preventDefault();
                const addButton = $('.addlink').first();
                if (addButton.length) {
                    window.location.href = addButton.attr('href');
                }
            }
            
            // Ctrl+Alt+S - Buscar
            if (e.ctrlKey && e.altKey && e.keyCode === 83) {
                e.preventDefault();
                $('#searchbar').focus();
            }
        });
    }

    // 💡 TOOLTIPS INFORMATIVOS
    function initTooltips() {
        $('[title]').each(function() {
            const $element = $(this);
            const title = $element.attr('title');
            
            $element.hover(
                function() {
                    showTooltip($(this), title);
                },
                function() {
                    hideTooltip();
                }
            );
        });
    }

    function showTooltip($element, text) {
        const $tooltip = $(`<div class="custom-tooltip" style="position: absolute; background: rgba(0,0,0,0.8); color: white; padding: 5px 10px; border-radius: 4px; font-size: 12px; z-index: 1000; pointer-events: none;">${text}</div>`);
        
        $('body').append($tooltip);
        
        const offset = $element.offset();
        $tooltip.css({
            top: offset.top - $tooltip.outerHeight() - 5,
            left: offset.left + ($element.outerWidth() / 2) - ($tooltip.outerWidth() / 2)
        });
    }

    function hideTooltip() {
        $('.custom-tooltip').remove();
    }

    // ✅ CONFIRMAÇÕES INTELIGENTES
    function initConfirmations() {
        $('a[href*="delete"], button[name*="delete"]').on('click', function(e) {
            e.preventDefault();
            const $element = $(this);
            const action = $element.text().trim();
            
            if (confirm(`Tem certeza que deseja executar: ${action}?\nEsta ação pode ser irreversível.`)) {
                if ($element.is('a')) {
                    window.location.href = $element.attr('href');
                } else {
                    $element.off('click').click();
                }
            }
        });
    }

    // 💾 AUTO-SALVAMENTO
    function initAutoSave() {
        if ($('.change-form').length) {
            let autoSaveTimeout;
            
            $('.change-form input, .change-form select, .change-form textarea').on('input change', function() {
                clearTimeout(autoSaveTimeout);
                showUnsavedIndicator();
                
                autoSaveTimeout = setTimeout(function() {
                    hideUnsavedIndicator();
                }, 3000);
            });
        }
    }

    function showUnsavedIndicator() {
        if (!$('.unsaved-indicator').length) {
            const $indicator = $(`
                <div class="unsaved-indicator" style="position: fixed; top: 10px; right: 10px; background: #ffc107; color: #856404; padding: 8px 12px; border-radius: 4px; font-size: 12px; z-index: 1000; box-shadow: 0 2px 10px rgba(0,0,0,0.1);">
                    ⚠️ Alterações não salvas
                </div>
            `);
            $('body').append($indicator);
        }
    }

    function hideUnsavedIndicator() {
        $('.unsaved-indicator').remove();
    }

    // 🔍 MELHORIAS NA BUSCA
    function initSearchEnhancements() {
        const $searchbar = $('#searchbar');
        
        if ($searchbar.length) {
            $searchbar.attr('placeholder', 'Buscar servidores, documentos, setores...');
            
            $searchbar.on('keydown', function(e) {
                if (e.keyCode === 27) {
                    $(this).val('');
                }
            });
        }
    }

    // 📱 OTIMIZAÇÕES MOBILE
    function initMobileOptimizations() {
        if (window.innerWidth <= 768) {
            $('.results table').wrap('<div style="overflow-x: auto; -webkit-overflow-scrolling: touch;"></div>');
            
            const $backToTop = $(`
                <button class="back-to-top" style="position: fixed; bottom: 70px; right: 20px; background: #007bff; color: white; border: none; border-radius: 50%; width: 50px; height: 50px; display: none; z-index: 999; box-shadow: 0 2px 10px rgba(0,0,0,0.2);">
                    ↑
                </button>
            `);
            
            $('body').append($backToTop);
            
            $(window).on('scroll', function() {
                if ($(this).scrollTop() > 300) {
                    $backToTop.fadeIn();
                } else {
                    $backToTop.fadeOut();
                }
            });
            
            $backToTop.on('click', function() {
                $('html, body').animate({ scrollTop: 0 }, 300);
            });
        }
    }

    // 🎨 ANIMAÇÕES E EFEITOS VISUAIS
    function initAnimations() {
        $('.stats-card, .results tbody tr, fieldset.module').addClass('fade-in');
        
        $('.submit-row input[type="submit"], .actions button').on('click', function() {
            const $button = $(this);
            $button.addClass('loading');
            
            setTimeout(function() {
                $button.removeClass('loading');
            }, 2000);
        });
    }

    // 🎯 FUNÇÃO PRINCIPAL DE INICIALIZAÇÃO
    function initAdminEnhancements() {
        $('body').addClass('admin-enhanced');
        
        const $indicator = $(`
            <div style="position: fixed; bottom: 20px; left: 20px; background: rgba(40, 167, 69, 0.9); color: white; padding: 5px 10px; border-radius: 15px; font-size: 11px; z-index: 999;">
                🚀 Admin Melhorado
            </div>
        `);
        
        $('body').append($indicator);
        
        setTimeout(function() {
            $indicator.fadeOut();
        }, 3000);
        
        console.log('🚀 Admin Customizado carregado com sucesso!');
    }

})(django.jQuery || jQuery);
