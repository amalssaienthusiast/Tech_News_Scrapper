import requests
import pandas as pd
from collections import Counter
import json
from datetime import datetime, timedelta
import time
from typing import Dict, List, Any
import matplotlib.pyplot as plt

class WebTrafficAnalyzer:
    """A class to handle web requests and analyze traffic patterns"""
    
    def __init__(self, base_url: str = None):
        """
        Initialize the analyzer with optional base URL
        
        Args:
            base_url (str): Base URL for all requests (optional)
        """
        self.base_url = base_url
        self.session = requests.Session()
        self.request_log = []
        self.traffic_data = {
            'requests': [],
            'responses': [],
            'timestamps': [],
            'endpoints': [],
            'status_codes': [],
            'response_times': []
        }
        
    def make_request(self, 
                    method: str = 'GET', 
                    endpoint: str = '', 
                    params: Dict = None, 
                    data: Dict = None, 
                    headers: Dict = None) -> Dict[str, Any]:
        """
        Make a web request and log its details
        
        Args:
            method (str): HTTP method (GET, POST, PUT, DELETE, etc.)
            endpoint (str): API endpoint or path
            params (Dict): Query parameters
            data (Dict): Request body data
            headers (Dict): Request headers
            
        Returns:
            Dict containing response data and metadata
        """
        url = f"{self.base_url}/{endpoint}" if self.base_url else endpoint
        
        start_time = time.time()
        
        try:
            response = self.session.request(
                method=method,
                url=url,
                params=params,
                json=data,
                headers=headers,
                timeout=10
            )
            
            response_time = time.time() - start_time
            
            # Log the request
            request_log = {
                'timestamp': datetime.now(),
                'method': method,
                'endpoint': endpoint,
                'status_code': response.status_code,
                'response_time': response_time,
                'response_size': len(response.content) if response.content else 0,
                'params': params,
                'headers_sent': headers
            }
            
            self.request_log.append(request_log)
            
            # Update traffic data
            self.traffic_data['requests'].append(1)
            self.traffic_data['responses'].append(response)
            self.traffic_data['timestamps'].append(datetime.now())
            self.traffic_data['endpoints'].append(endpoint)
            self.traffic_data['status_codes'].append(response.status_code)
            self.traffic_data['response_times'].append(response_time)
            
            return {
                'success': True,
                'status_code': response.status_code,
                'response_time': response_time,
                'data': response.json() if response.headers.get('content-type') == 'application/json' else response.text,
                'headers': dict(response.headers),
                'request_info': request_log
            }
            
        except requests.exceptions.RequestException as e:
            return {
                'success': False,
                'error': str(e),
                'request_info': {
                    'timestamp': datetime.now(),
                    'method': method,
                    'endpoint': endpoint,
                    'error': str(e)
                }
            }
    
    def analyze_traffic_patterns(self) -> Dict[str, Any]:
        """
        Analyze collected traffic data
        
        Returns:
            Dict containing traffic analysis metrics
        """
        if not self.request_log:
            return {"error": "No traffic data collected"}
        
        # Convert logs to DataFrame for analysis
        df = pd.DataFrame(self.request_log)
        
        analysis = {
            'total_requests': len(self.request_log),
            'successful_requests': len([log for log in self.request_log if 'status_code' in log and log['status_code'] < 400]),
            'failed_requests': len([log for log in self.request_log if 'status_code' in log and log['status_code'] >= 400]),
        }
        
        # Status code distribution
        status_codes = [log.get('status_code') for log in self.request_log if 'status_code' in log]
        if status_codes:
            analysis['status_code_distribution'] = dict(Counter(status_codes))
        
        # Endpoint usage
        endpoints = [log.get('endpoint') for log in self.request_log if 'endpoint' in log]
        if endpoints:
            analysis['endpoint_distribution'] = dict(Counter(endpoints))
        
        # Response time analysis
        response_times = [log.get('response_time') for log in self.request_log if 'response_time' in log]
        if response_times:
            analysis['response_time_stats'] = {
                'avg_response_time': sum(response_times) / len(response_times),
                'max_response_time': max(response_times),
                'min_response_time': min(response_times),
                'median_response_time': sorted(response_times)[len(response_times)//2]
            }
        
        # Time-based analysis
        if 'timestamp' in df.columns:
            df['hour'] = df['timestamp'].dt.hour
            df['minute'] = df['timestamp'].dt.minute
            
            analysis['hourly_traffic'] = df.groupby('hour').size().to_dict()
            analysis['peak_hour'] = df.groupby('hour').size().idxmax() if not df.groupby('hour').size().empty else None
        
        # Method distribution
        methods = [log.get('method') for log in self.request_log if 'method' in log]
        if methods:
            analysis['method_distribution'] = dict(Counter(methods))
        
        return analysis
    
    def generate_traffic_report(self, output_file: str = 'traffic_report.json') -> str:
        """
        Generate a comprehensive traffic report
        
        Args:
            output_file (str): Path to save the report
            
        Returns:
            Path to the saved report
        """
        analysis = self.analyze_traffic_patterns()
        
        report = {
            'generated_at': datetime.now().isoformat(),
            'analysis_period': {
                'start': min(self.traffic_data['timestamps']).isoformat() if self.traffic_data['timestamps'] else None,
                'end': max(self.traffic_data['timestamps']).isoformat() if self.traffic_data['timestamps'] else None
            },
            'traffic_summary': analysis,
            'sample_requests': self.request_log[:10]  # Include first 10 requests as sample
        }
        
        with open(output_file, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        return output_file
    
    def visualize_traffic(self, save_path: str = 'traffic_visualization.png'):
        """
        Create visualizations of traffic patterns
        
        Args:
            save_path (str): Path to save the visualization
        """
        if not self.request_log:
            print("No data to visualize")
            return
        
        df = pd.DataFrame(self.request_log)
        
        fig, axes = plt.subplots(2, 2, figsize=(15, 10))
        
        # 1. Status Code Distribution
        if 'status_code' in df.columns:
            status_counts = df['status_code'].value_counts()
            axes[0, 0].bar(status_counts.index.astype(str), status_counts.values)
            axes[0, 0].set_title('Status Code Distribution')
            axes[0, 0].set_xlabel('Status Code')
            axes[0, 0].set_ylabel('Count')
        
        # 2. Endpoint Usage
        if 'endpoint' in df.columns:
            endpoint_counts = df['endpoint'].value_counts().head(10)  # Top 10 endpoints
            axes[0, 1].bar(endpoint_counts.index, endpoint_counts.values)
            axes[0, 1].set_title('Top 10 Endpoints')
            axes[0, 1].set_xlabel('Endpoint')
            axes[0, 1].set_ylabel('Count')
            axes[0, 1].tick_params(axis='x', rotation=45)
        
        # 3. Response Time Distribution
        if 'response_time' in df.columns:
            axes[1, 0].hist(df['response_time'], bins=20, edgecolor='black')
            axes[1, 0].set_title('Response Time Distribution')
            axes[1, 0].set_xlabel('Response Time (seconds)')
            axes[1, 0].set_ylabel('Frequency')
        
        # 4. Hourly Traffic
        if 'timestamp' in df.columns:
            df['hour'] = df['timestamp'].dt.hour
            hourly_counts = df.groupby('hour').size()
            axes[1, 1].plot(hourly_counts.index, hourly_counts.values, marker='o')
            axes[1, 1].set_title('Hourly Traffic Pattern')
            axes[1, 1].set_xlabel('Hour of Day')
            axes[1, 1].set_ylabel('Request Count')
        
        plt.tight_layout()
        plt.savefig(save_path)
        plt.show()
        
        return save_path
    
    def get_performance_metrics(self) -> Dict[str, float]:
        """
        Calculate performance metrics from traffic data
        
        Returns:
            Dict containing performance metrics
        """
        if not self.request_log:
            return {}
        
        df = pd.DataFrame(self.request_log)
        
        metrics = {}
        
        if 'status_code' in df.columns and 'response_time' in df.columns:
            # Calculate success rate
            success_rate = (df['status_code'] < 400).mean() * 100
            metrics['success_rate_percent'] = round(success_rate, 2)
            
            # Calculate average response time for successful requests
            avg_success_time = df[df['status_code'] < 400]['response_time'].mean()
            metrics['avg_success_response_time'] = round(avg_success_time, 4)
        
        return metrics
    
    def simulate_traffic(self, 
                        endpoints: List[str], 
                        duration_seconds: int = 60, 
                        requests_per_second: int = 5):
        """
        Simulate traffic to test the platform
        
        Args:
            endpoints (List[str]): List of endpoints to hit
            duration_seconds (int): Duration of simulation in seconds
            requests_per_second (int): Requests per second
        """
        import random
        from concurrent.futures import ThreadPoolExecutor
        
        start_time = time.time()
        
        def make_simulated_request():
            endpoint = random.choice(endpoints)
            method = random.choice(['GET', 'POST'])
            
            # Simulate different types of requests
            params = {'page': random.randint(1, 10)} if method == 'GET' else None
            data = {'data': 'test'} if method == 'POST' else None
            
            return self.make_request(
                method=method,
                endpoint=endpoint,
                params=params,
                data=data
            )
        
        # Use thread pool for concurrent requests
        with ThreadPoolExecutor(max_workers=10) as executor:
            while time.time() - start_time < duration_seconds:
                futures = []
                for _ in range(requests_per_second):
                    futures.append(executor.submit(make_simulated_request))
                
                # Wait for all requests to complete
                for future in futures:
                    future.result()
                
                time.sleep(1)  # Wait for next second


# Example usage:
if __name__ == "__main__":
    # Initialize analyzer with a base URL
    analyzer = WebTrafficAnalyzer(base_url="https://api.example.com")
    
    # Make some requests
    print("Making sample requests...")
    result1 = analyzer.make_request('GET', 'users', params={'page': 1})
    result2 = analyzer.make_request('POST', 'auth/login', data={'username': 'test', 'password': 'test'})
    result3 = analyzer.make_request('GET', 'products', params={'category': 'electronics'})
    
    # Analyze traffic
    print("\nTraffic Analysis:")
    analysis = analyzer.analyze_traffic_patterns()
    print(json.dumps(analysis, indent=2))
    
    # Get performance metrics
    print("\nPerformance Metrics:")
    metrics = analyzer.get_performance_metrics()
    print(json.dumps(metrics, indent=2))
    
    # Generate report
    report_path = analyzer.generate_traffic_report('web_traffic_report.json')
    print(f"\nReport generated: {report_path}")
    
    # Visualize traffic (uncomment to generate plots)
    # analyzer.visualize_traffic()
    
    # Simulate traffic (uncomment to run simulation)
    # print("\nSimulating traffic...")
    # analyzer.simulate_traffic(
    #     endpoints=['users', 'products', 'orders', 'auth/login'],
    #     duration_seconds=30,
    #     requests_per_second=3
    # )