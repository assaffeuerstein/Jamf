/**
 * Add/Remove Mac Pipeline
 * 
 * This pipeline orchestrates the process of adding or removing Mac hosts
 * from the infrastructure. It updates DNS, DHCP, generates Ansible host_vars,
 * and commits changes to Git.
 * 
 * Parameters:
 *   - ACTION: add or remove
 *   - CSV_FILE: Path to CSV file with hostname,mac,ip data
 *   - DOMAIN: Domain suffix for hostnames (e.g., macfarm.example.com)
 *   - DRY_RUN: If true, shows what would be done without making changes
 * 
 * Required Credentials:
 *   - powerdns-api-key: PowerDNS API key (secret text)
 *   - github-credentials: GitHub username/token for Git operations
 *   - nautobot-token: Nautobot API token (optional)
 */

pipeline {
    agent any
    
    options {
        buildDiscarder(logRotator(numToKeepStr: '30'))
        timestamps()
        ansiColor('xterm')
        disableConcurrentBuilds()
    }
    
    parameters {
        choice(
            name: 'ACTION',
            choices: ['add', 'remove'],
            description: 'Action to perform: add new hosts or remove existing ones'
        )
        file(
            name: 'CSV_FILE',
            description: 'CSV file with hostname,mac,ip columns'
        )
        string(
            name: 'DOMAIN',
            defaultValue: 'macfarm.example.com',
            description: 'Domain suffix for hostnames'
        )
        booleanParam(
            name: 'DRY_RUN',
            defaultValue: false,
            description: 'If checked, shows what would be done without making changes'
        )
        booleanParam(
            name: 'SKIP_DNS',
            defaultValue: false,
            description: 'Skip DNS update step'
        )
        booleanParam(
            name: 'SKIP_DHCP',
            defaultValue: false,
            description: 'Skip DHCP update step'
        )
        booleanParam(
            name: 'SKIP_NAUTOBOT',
            defaultValue: true,
            description: 'Skip Nautobot IPAM update step'
        )
        booleanParam(
            name: 'SKIP_DEPLOY',
            defaultValue: false,
            description: 'Skip DHCP deployment step'
        )
        booleanParam(
            name: 'SKIP_HOST_VARS',
            defaultValue: false,
            description: 'Skip Ansible host_vars generation'
        )
        booleanParam(
            name: 'SKIP_GIT_COMMIT',
            defaultValue: false,
            description: 'Skip Git commit and push'
        )
    }
    
    environment {
        POWERDNS_API_KEY = credentials('powerdns-api-key')
        POWERDNS_SERVER_URL = "${env.POWERDNS_URL ?: 'http://localhost:8084'}"
        NAUTOBOT_URL = "${env.NAUTOBOT_URL ?: 'http://localhost:8000'}"
        NAUTOBOT_TOKEN = credentials('nautobot-token')
        REPO_DIR = "${WORKSPACE}/mac-infrastructure"
        SCRIPTS_DIR = "${REPO_DIR}/scripts"
        ANSIBLE_DIR = "${REPO_DIR}/ansible"
    }
    
    stages {
        stage('Prepare Workspace') {
            steps {
                script {
                    echo "=".multiply(60)
                    echo "Mac Infrastructure Management Pipeline"
                    echo "=".multiply(60)
                    echo "Action: ${params.ACTION}"
                    echo "Domain: ${params.DOMAIN}"
                    echo "Dry Run: ${params.DRY_RUN}"
                    echo "=".multiply(60)
                }
                
                // Clone or update repository
                dir("${REPO_DIR}") {
                    git branch: 'main',
                        credentialsId: 'github-credentials',
                        url: 'https://github.com/your-org/mac-infrastructure.git'
                }
                
                // Copy uploaded CSV file
                script {
                    if (params.CSV_FILE) {
                        sh "cp '${params.CSV_FILE}' ${WORKSPACE}/hosts.csv"
                    } else {
                        error "CSV file is required"
                    }
                }
                
                // Validate CSV format
                sh """
                    echo "Validating CSV file..."
                    head -5 ${WORKSPACE}/hosts.csv
                    wc -l ${WORKSPACE}/hosts.csv
                """
            }
        }
        
        stage('Update DNS (PowerDNS)') {
            when {
                expression { !params.SKIP_DNS }
            }
            steps {
                script {
                    def dryRunFlag = params.DRY_RUN ? '--dry-run' : ''
                    
                    sh """
                        cd ${SCRIPTS_DIR}
                        python3 powerdns_manager.py \\
                            --file ${WORKSPACE}/hosts.csv \\
                            --domain ${params.DOMAIN} \\
                            --action ${params.ACTION} \\
                            ${dryRunFlag}
                    """
                }
            }
        }
        
        stage('Update Nautobot IPAM') {
            when {
                expression { !params.SKIP_NAUTOBOT }
            }
            steps {
                script {
                    def dryRunFlag = params.DRY_RUN ? '--dry-run' : ''
                    
                    sh """
                        cd ${SCRIPTS_DIR}
                        python3 nautobot_manager.py \\
                            --file ${WORKSPACE}/hosts.csv \\
                            --action ${params.ACTION} \\
                            ${dryRunFlag}
                    """
                }
            }
        }
        
        stage('Update DHCP Configuration') {
            when {
                expression { !params.SKIP_DHCP }
            }
            steps {
                script {
                    def dryRunFlag = params.DRY_RUN ? '--dry-run' : ''
                    def dhcpdConf = "${ANSIBLE_DIR}/roles/dhcpd/files/dhcpd.conf"
                    
                    sh """
                        cd ${SCRIPTS_DIR}
                        python3 dhcp_reservation_manager.py \\
                            --file ${WORKSPACE}/hosts.csv \\
                            --domain ${params.DOMAIN} \\
                            --config ${dhcpdConf} \\
                            --action ${params.ACTION} \\
                            ${dryRunFlag}
                    """
                }
            }
        }
        
        stage('Deploy DHCP Configuration') {
            when {
                expression { !params.SKIP_DEPLOY && !params.DRY_RUN }
            }
            steps {
                script {
                    sh """
                        cd ${ANSIBLE_DIR}
                        ansible-playbook -i hosts.ini deploy-dhcpd.yml
                    """
                }
            }
        }
        
        stage('Generate Ansible Host Vars') {
            when {
                expression { !params.SKIP_HOST_VARS && params.ACTION == 'add' }
            }
            steps {
                script {
                    def dryRunFlag = params.DRY_RUN ? '--dry-run' : ''
                    
                    sh """
                        cd ${SCRIPTS_DIR}
                        python3 host_vars_generator.py \\
                            --file ${WORKSPACE}/hosts.csv \\
                            --output-dir ${ANSIBLE_DIR}/host_vars \\
                            --force \\
                            ${dryRunFlag}
                    """
                }
            }
        }
        
        stage('Commit and Push Changes') {
            when {
                expression { !params.SKIP_GIT_COMMIT && !params.DRY_RUN }
            }
            steps {
                withCredentials([usernamePassword(
                    credentialsId: 'github-credentials',
                    usernameVariable: 'GIT_USER',
                    passwordVariable: 'GIT_TOKEN'
                )]) {
                    dir("${REPO_DIR}") {
                        sh """
                            git config user.name "Jenkins"
                            git config user.email "jenkins@example.com"
                            
                            # Add changed files
                            git add ansible/roles/dhcpd/files/dhcpd.conf
                            git add ansible/host_vars/
                            git add ansible/hosts.ini
                            
                            # Check if there are changes to commit
                            if git diff --cached --quiet; then
                                echo "No changes to commit"
                            else
                                git commit -m "[Jenkins] ${params.ACTION} Mac hosts - Build #${BUILD_NUMBER}"
                                
                                # Push changes
                                git push https://\${GIT_USER}:\${GIT_TOKEN}@github.com/your-org/mac-infrastructure.git main
                            fi
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
            echo "Successfully ${params.ACTION == 'add' ? 'added' : 'removed'} Mac hosts"
        }
        
        failure {
            echo "Pipeline failed. Check logs for details."
        }
        
        cleanup {
            cleanWs()
        }
    }
}

