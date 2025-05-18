#!/bin/bash
# Script para configurar el entorno de Git para el proyecto NGX Agents

echo "Configurando entorno de Git para NGX Agents..."

# Verificar si Git está instalado
if ! command -v git &> /dev/null; then
    echo "Error: Git no está instalado. Por favor, instala Git antes de continuar."
    exit 1
fi

# Configurar hooks personalizados
echo "Configurando hooks personalizados..."
git config core.hooksPath .githooks

# Verificar si los hooks existen y son ejecutables
if [ ! -x ".githooks/pre-commit" ] || [ ! -x ".githooks/commit-msg" ]; then
    echo "Haciendo ejecutables los hooks..."
    chmod +x .githooks/pre-commit .githooks/commit-msg
fi

# Configurar alias útiles
echo "Configurando alias útiles..."
git config --local alias.st status
git config --local alias.co checkout
git config --local alias.br branch
git config --local alias.ci commit
git config --local alias.lg "log --color --graph --pretty=format:'%Cred%h%Creset -%C(yellow)%d%Creset %s %Cgreen(%cr) %C(bold blue)<%an>%Creset' --abbrev-commit"

# Configurar comportamiento de pull
echo "Configurando comportamiento de pull..."
git config --local pull.rebase true

# Configurar usuario y correo si no están configurados
if [ -z "$(git config --local user.name)" ]; then
    echo "Configurando usuario y correo..."
    read -p "Ingresa tu nombre: " name
    read -p "Ingresa tu correo: " email
    git config --local user.name "$name"
    git config --local user.email "$email"
fi

# Verificar configuración de fin de línea
echo "Verificando configuración de fin de línea..."
if [ -z "$(git config --local core.autocrlf)" ]; then
    git config --local core.autocrlf input
fi

echo "Configuración de Git completada con éxito."
echo "Recuerda seguir las convenciones de commit:"
echo "  Feat(component): add new component"
echo "  Fix(api): fix api error"
echo "  Docs(readme): update readme"
echo "  Refactor(utils): refactor utils"
echo "  Style(tailwind): add new tailwind class"
echo "  Test(unit): add unit test"
echo "  Chore(deps): update dependencies"
