/**
 * Mac Base Configuration Pipeline
 * 
 * This pipeline applies base configuration to Mac machines using Ansible.
 * It can target specific hosts or groups from the inventory.
 * 
 * Parameters:
 *   - TARGET: Ansible host pattern (hostname, group, or 'all')
 *   - TAGS: Ansible tags to run (comma-separated, or 'all')
 *   - CHECK_MODE: Run in check mode (dry run)
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
    }
    
    parameters {
        string(
            name: 'TARGET',
            defaultValue: '',
            description: 'Ansible target pattern: hostname, group name, or "all". Leave empty to be prompted.'
        )
        string(
            name: 'TAGS',
            defaultValue: 'all',
            description: 'Ansible tags to run (comma-separated): network, hostname, ssh, power, homebrew, or "all"'
        )
        booleanParam(
            name: 'CHECK_MODE',
            defaultValue: false,
            description: 'Run in check mode (dry run) - no changes will be made'
        )
        booleanParam(
            name: 'VERBOSE',
            defaultValue: false,
            description: 'Run Ansible in verbose mode (-vv)'
        )
        choice(
            name: 'PLAYBOOK',
            choices: [
                'mac-mini-base-config.yml',
                'install-xcode-cli-tools.yml'
            ],
            description: 'Playbook to execute'
        )
    }
    
    environment {
        REPO_DIR = "${WORKSPACE}/mac-infrastructure"
        ANSIBLE_DIR = "${REPO_DIR}/ansible"
        ANSIBLE_HOST_KEY_CHECKING = 'False'
        ANSIBLE_TIMEOUT = '30'
    }
    
    stages {
        stage('Validate Parameters') {
            steps {
                script {
                    if (!params.TARGET?.trim()) {
                        error "TARGET parameter is required. Specify a hostname, group, or 'all'."
                    }
                    
                    echo "=".multiply(60)
                    echo "Mac Base Configuration Pipeline"
                    echo "=".multiply(60)
                    echo "Target: ${params.TARGET}"
                    echo "Playbook: ${params.PLAYBOOK}"
                    echo "Tags: ${params.TAGS}"
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
        
        stage('Verify Ansible') {
            steps {
                sh """
                    ansible --version
                    ansible-playbook --version
                """
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
                            --private-key=\${SSH_KEY} \\
                            -o || echo "Some hosts may be unreachable"
                    """
                }
            }
        }
        
        stage('Run Ansible Playbook') {
            steps {
                withCredentials([sshUserPrivateKey(
                    credentialsId: 'ssh-key-macfarm',
                    keyFileVariable: 'SSH_KEY'
                )]) {
                    script {
                        def checkFlag = params.CHECK_MODE ? '--check' : ''
                        def verboseFlag = params.VERBOSE ? '-vv' : ''
                        def tagsFlag = params.TAGS != 'all' ? "--tags '${params.TAGS}'" : ''
                        
                        sh """
                            cd ${ANSIBLE_DIR}
                            ansible-playbook -i hosts.ini ${params.PLAYBOOK} \\
                                --limit '${params.TARGET}' \\
                                --private-key=\${SSH_KEY} \\
                                ${checkFlag} \\
                                ${verboseFlag} \\
                                ${tagsFlag} \\
                                --diff
                        """
                    }
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
            echo "Successfully configured Mac hosts: ${params.TARGET}"
        }
        
        failure {
            echo "Pipeline failed. Check Ansible output for details."
        }
        
        cleanup {
            cleanWs()
        }
    }
}

