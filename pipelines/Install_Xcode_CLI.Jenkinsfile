/**
 * Xcode CLI Tools Installation Pipeline
 * 
 * This pipeline installs Xcode Command Line Tools on Mac machines.
 * It uses Ansible to ensure consistent installation across multiple hosts.
 * 
 * Parameters:
 *   - TARGET: Ansible host pattern (hostname, group, or 'all')
 *   - FORCE_REINSTALL: Force reinstall even if already present
 * 
 * Required Credentials:
 *   - ssh-key-macfarm: SSH private key for Mac access
 *   - github-credentials: GitHub credentials for repository access
 */

pipeline {
    agent any
    
    options {
        buildDiscarder(logRotator(numToKeepStr: '30'))
        timestamps()
        ansiColor('xterm')
        timeout(time: 2, unit: 'HOURS')
    }
    
    parameters {
        string(
            name: 'TARGET',
            defaultValue: '',
            description: 'Ansible target pattern: hostname, group name, or "all"'
        )
        booleanParam(
            name: 'FORCE_REINSTALL',
            defaultValue: false,
            description: 'Force reinstall even if Xcode CLI tools are already present'
        )
        booleanParam(
            name: 'CHECK_MODE',
            defaultValue: false,
            description: 'Run in check mode (dry run)'
        )
    }
    
    environment {
        REPO_DIR = "${WORKSPACE}/mac-infrastructure"
        ANSIBLE_DIR = "${REPO_DIR}/ansible"
        ANSIBLE_HOST_KEY_CHECKING = 'False'
        ANSIBLE_TIMEOUT = '60'
    }
    
    stages {
        stage('Validate Parameters') {
            steps {
                script {
                    if (!params.TARGET?.trim()) {
                        error "TARGET parameter is required."
                    }
                    
                    echo "=".multiply(60)
                    echo "Xcode CLI Tools Installation Pipeline"
                    echo "=".multiply(60)
                    echo "Target: ${params.TARGET}"
                    echo "Force Reinstall: ${params.FORCE_REINSTALL}"
                    echo "Check Mode: ${params.CHECK_MODE}"
                    echo "=".multiply(60)
                }
            }
        }
        
        stage('Checkout Repository') {
            steps {
                dir("${REPO_DIR}") {
                    git branch: 'main',
                        credentialsId: 'github-credentials',
                        url: 'https://github.com/your-org/mac-infrastructure.git'
                }
            }
        }
        
        stage('Test Connectivity') {
            steps {
                withCredentials([sshUserPrivateKey(
                    credentialsId: 'ssh-key-macfarm',
                    keyFileVariable: 'SSH_KEY'
                )]) {
                    sh """
                        cd ${ANSIBLE_DIR}
                        ansible -i hosts.ini ${params.TARGET} -m ping \\
                            --private-key=\${SSH_KEY}
                    """
                }
            }
        }
        
        stage('Check Current Status') {
            steps {
                withCredentials([sshUserPrivateKey(
                    credentialsId: 'ssh-key-macfarm',
                    keyFileVariable: 'SSH_KEY'
                )]) {
                    sh """
                        cd ${ANSIBLE_DIR}
                        ansible -i hosts.ini ${params.TARGET} \\
                            --private-key=\${SSH_KEY} \\
                            -m shell -a "xcode-select -p 2>/dev/null || echo 'Not installed'" \\
                            -o
                    """
                }
            }
        }
        
        stage('Install Xcode CLI Tools') {
            steps {
                withCredentials([sshUserPrivateKey(
                    credentialsId: 'ssh-key-macfarm',
                    keyFileVariable: 'SSH_KEY'
                )]) {
                    script {
                        def checkFlag = params.CHECK_MODE ? '--check' : ''
                        def extraVars = params.FORCE_REINSTALL ? '-e force_reinstall=true' : ''
                        
                        sh """
                            cd ${ANSIBLE_DIR}
                            ansible-playbook -i hosts.ini install-xcode-cli-tools.yml \\
                                --limit '${params.TARGET}' \\
                                --private-key=\${SSH_KEY} \\
                                ${checkFlag} \\
                                ${extraVars} \\
                                -v
                        """
                    }
                }
            }
        }
        
        stage('Verify Installation') {
            when {
                expression { !params.CHECK_MODE }
            }
            steps {
                withCredentials([sshUserPrivateKey(
                    credentialsId: 'ssh-key-macfarm',
                    keyFileVariable: 'SSH_KEY'
                )]) {
                    sh """
                        cd ${ANSIBLE_DIR}
                        ansible -i hosts.ini ${params.TARGET} \\
                            --private-key=\${SSH_KEY} \\
                            -m shell -a "xcode-select -p && git --version"
                    """
                }
            }
        }
    }
    
    post {
        always {
            script {
                echo "=".multiply(60)
                echo "Pipeline completed with status: ${currentBuild.currentResult}"
                echo "=".multiply(60)
            }
        }
        
        success {
            echo "Successfully installed Xcode CLI tools on: ${params.TARGET}"
        }
        
        failure {
            echo "Pipeline failed. Some hosts may not have Xcode CLI tools installed."
        }
        
        cleanup {
            cleanWs()
        }
    }
}

