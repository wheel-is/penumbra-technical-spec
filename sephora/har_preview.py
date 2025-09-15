#!/usr/bin/env python3
"""
HAR Preview Tool - Navigate through HAR file requests one at a time
to understand the gift card ordering flow.
"""

import argparse
import json
import sys
from typing import Dict, List, Any
from datetime import datetime
import re
import requests
from urllib.parse import urlparse
import time
import textwrap

class HARPreview:
    def __init__(self, har_file_path: str):
        self.har_file_path = har_file_path
        self.entries = []
        self.current_index = 0
        self.load_har_file()
    
    def load_har_file(self):
        """Load and parse the HAR file"""
        try:
            with open(self.har_file_path, 'r', encoding='utf-8') as f:
                har_data = json.load(f)
                self.entries = har_data.get('log', {}).get('entries', [])
                print(f"Loaded {len(self.entries)} requests from {self.har_file_path}")
        except Exception as e:
            print(f"Error loading HAR file: {e}")
            sys.exit(1)
    
    def format_request_info(self, entry: Dict[str, Any]) -> str:
        """Format request information for display"""
        request = entry.get('request', {})
        response = entry.get('response', {})
        
        # Basic request info
        method = request.get('method', 'UNKNOWN')
        url = request.get('url', 'UNKNOWN')
        status = response.get('status', 'NO_RESPONSE')
        
        # Clean up long URLs for display
        display_url = url
        if len(url) > 100:
            display_url = url[:100] + "..."
        
        # Extract domain and path
        domain_match = re.search(r'https?://([^/]+)', url)
        domain = domain_match.group(1) if domain_match else 'unknown'
        
        # Get timestamp
        timestamp = entry.get('startedDateTime', '')
        if timestamp:
            try:
                dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                timestamp = dt.strftime('%H:%M:%S')
            except:
                timestamp = timestamp[:19]  # Fallback
        
        # Check for interesting headers
        headers = request.get('headers', [])
        auth_header = next((h['value'] for h in headers if h['name'].lower() == 'authorization'), None)
        content_type = next((h['value'] for h in headers if h['name'].lower() == 'content-type'), None)
        
        # Get request body if present
        post_data = request.get('postData', {})
        request_body = post_data.get('text', '') if post_data else ''
        
        # Format output
        output = []
        output.append("=" * 80)
        output.append(f"Request #{self.current_index + 1}/{len(self.entries)}")
        output.append(f"Time: {timestamp}")
        output.append(f"Method: {method}")
        output.append(f"Status: {status}")
        output.append(f"Domain: {domain}")
        output.append(f"URL: {display_url}")
        
        if content_type:
            output.append(f"Content-Type: {content_type}")
        
        if auth_header:
            auth_preview = auth_header[:50] + "..." if len(auth_header) > 50 else auth_header
            output.append(f"Authorization: {auth_preview}")
        
        # Show interesting query parameters
        if '?' in url:
            query_part = url.split('?', 1)[1]
            if query_part:
                output.append("Query Parameters:")
                for param in query_part.split('&')[:5]:  # Show first 5 params
                    if '=' in param:
                        key, value = param.split('=', 1)
                        if len(value) > 50:
                            value = value[:50] + "..."
                        output.append(f"  {key}: {value}")
        
        # Show request body if it's JSON and not too long
        if request_body and method in ['POST', 'PUT', 'PATCH']:
            output.append("Request Body:")
            try:
                if request_body.startswith('{') or request_body.startswith('['):
                    body_json = json.loads(request_body)
                    body_str = json.dumps(body_json, indent=2)
                    # if len(body_str) > 500:
                    #     body_str = body_str[:500] + "\n... (truncated)"
                    output.append(body_str)
                else:
                    if len(request_body) > 200:
                        output.append(request_body[:200] + "... (truncated)")
                    else:
                        output.append(request_body)
            except:
                if len(request_body) > 200:
                    output.append(request_body[:200] + "... (truncated)")
                else:
                    output.append(request_body)
        
        # Show response content type and size
        response_headers = response.get('headers', [])
        response_content_type = next((h['value'] for h in response_headers if h['name'].lower() == 'content-type'), None)
        if response_content_type:
            output.append(f"Response Content-Type: {response_content_type}")
        
        content = response.get('content', {})
        if content.get('size'):
            output.append(f"Response Size: {content['size']} bytes")
        
        return '\n'.join(output)
    
    def format_response_details(self, entry: Dict[str, Any]) -> str:
        """Format complete response information including all headers and body"""
        response = entry.get('response', {})
        
        output = []
        output.append("=" * 80)
        output.append("RESPONSE DETAILS")
        output.append("=" * 80)
        
        # Response status
        status = response.get('status', 'NO_RESPONSE')
        status_text = response.get('statusText', '')
        http_version = response.get('httpVersion', '')
        
        output.append(f"Status: {status} {status_text}")
        if http_version:
            output.append(f"HTTP Version: {http_version}")
        
        # Response headers
        headers = response.get('headers', [])
        if headers:
            output.append("\nResponse Headers:")
            for header in headers:
                name = header.get('name', '')
                value = header.get('value', '')
                output.append(f"  {name}: {value}")
        
        # Response cookies
        cookies = response.get('cookies', [])
        if cookies:
            output.append("\nResponse Cookies:")
            for cookie in cookies:
                name = cookie.get('name', '')
                value = cookie.get('value', '')
                domain = cookie.get('domain', '')
                path = cookie.get('path', '')
                output.append(f"  {name}={value} (domain: {domain}, path: {path})")
        
        # Response content
        content = response.get('content', {})
        if content:
            size = content.get('size', 0)
            mime_type = content.get('mimeType', '')
            encoding = content.get('encoding', '')
            text = content.get('text', '')
            
            output.append(f"\nResponse Content:")
            output.append(f"  MIME Type: {mime_type}")
            output.append(f"  Size: {size} bytes")
            if encoding:
                output.append(f"  Encoding: {encoding}")
            
            if text:
                output.append("\nResponse Body:")
                try:
                    # Try to parse as JSON for pretty printing
                    if text.startswith('{') or text.startswith('['):
                        json_data = json.loads(text)
                        formatted_json = json.dumps(json_data, indent=2)
                        output.append(formatted_json)
                    else:
                        # Show raw text
                        output.append(text)
                except json.JSONDecodeError:
                    # If not JSON, show raw text
                    output.append(text)
        
        return '\n'.join(output)
    
    def show_complete_request(self, entry: Dict[str, Any]) -> str:
        """Show both request and response details for a complete view"""
        request_info = self.format_request_info(entry)
        response_info = self.format_response_details(entry)
        
        return f"{request_info}\n\n{response_info}"
    
    def extract_request_details(self, entry: Dict[str, Any]) -> Dict[str, Any]:
        """Extract request details from HAR entry for live execution"""
        request = entry.get('request', {})
        
        # Basic request info
        method = request.get('method', 'GET')
        url = request.get('url', '')
        
        # Headers
        headers = {}
        for header in request.get('headers', []):
            name = header.get('name', '')
            value = header.get('value', '')
            # Skip pseudo-headers and problematic headers
            if not name.startswith(':') and name.lower() not in [
                'host', 'content-length', 'connection', 'upgrade-insecure-requests',
                'accept-encoding'  # Let requests handle encoding
            ]:
                headers[name] = value
        
        # Request body
        body = None
        post_data = request.get('postData', {})
        if post_data:
            body = post_data.get('text', '')
        
        # Query parameters (already in URL, but extract for visibility)
        query_params = []
        if '?' in url:
            query_part = url.split('?', 1)[1]
            for param in query_part.split('&'):
                if '=' in param:
                    key, value = param.split('=', 1)
                    query_params.append((key, value))
        
        return {
            'method': method,
            'url': url,
            'headers': headers,
            'body': body,
            'query_params': query_params,
            'original_entry': entry
        }
    
    def execute_request_live(self, entry: Dict[str, Any], timeout: int = 30) -> Dict[str, Any]:
        """Execute a request from HAR entry live and return response details"""
        request_details = self.extract_request_details(entry)
        
        print("=" * 80)
        print("EXECUTING REQUEST LIVE")
        print("=" * 80)
        print(f"Method: {request_details['method']}")
        print(f"URL: {request_details['url']}")
        print(f"Headers: {len(request_details['headers'])} headers")
        if request_details['body']:
            print(f"Body: {len(request_details['body'])} characters")
        print()
        print("Making request...")
        
        start_time = time.time()
        
        try:
            # Make the actual HTTP request
            response = requests.request(
                method=request_details['method'],
                url=request_details['url'],
                headers=request_details['headers'],
                data=request_details['body'],
                timeout=timeout,
                allow_redirects=True,
                verify=True  # Verify SSL certificates
            )
            
            end_time = time.time()
            response_time = (end_time - start_time) * 1000  # Convert to milliseconds
            
            # Format the live response
            result = {
                'success': True,
                'status_code': response.status_code,
                'reason': response.reason,
                'headers': dict(response.headers),
                'content': response.text,
                'content_bytes': response.content,
                'response_time_ms': response_time,
                'url': response.url,  # Final URL after redirects
                'request_details': request_details
            }
            
            print(f"\u2705 Request completed in {response_time:.2f}ms")
            print(f"Status: {response.status_code} {response.reason}")
            
            return result
            
        except requests.exceptions.Timeout:
            return {
                'success': False,
                'error': f'Request timed out after {timeout} seconds',
                'request_details': request_details
            }
        except requests.exceptions.ConnectionError as e:
            return {
                'success': False,
                'error': f'Connection error: {str(e)}',
                'request_details': request_details
            }
        except requests.exceptions.RequestException as e:
            return {
                'success': False,
                'error': f'Request failed: {str(e)}',
                'request_details': request_details
            }
        except Exception as e:
            return {
                'success': False,
                'error': f'Unexpected error: {str(e)}',
                'request_details': request_details
            }
    
    def format_live_response(self, result: Dict[str, Any]) -> str:
        """Format live response for display"""
        output = []
        
        if not result['success']:
            output.append("=" * 80)
            output.append("REQUEST FAILED")
            output.append("=" * 80)
            output.append(f"Error: {result['error']}")
            return '\n'.join(output)
        
        output.append("=" * 80)
        output.append("LIVE RESPONSE")
        output.append("=" * 80)
        
        # Response status and timing
        output.append(f"Status: {result['status_code']} {result['reason']}")
        output.append(f"Response Time: {result['response_time_ms']:.2f}ms")
        output.append(f"Final URL: {result['url']}")
        
        # Response headers
        output.append("\nResponse Headers:")
        for name, value in result['headers'].items():
            output.append(f"  {name}: {value}")
        
        # Response content
        content = result['content']
        if content:
            output.append(f"\nResponse Content ({len(content)} characters):")
            try:
                # Try to parse as JSON for pretty printing
                if content.strip().startswith(('{', '[')):
                    json_data = json.loads(content)
                    formatted_json = json.dumps(json_data, indent=2)
                    output.append(formatted_json)
                else:
                    # Show raw text (truncate if too long)
                    if len(content) > 2000:
                        output.append(content[:2000] + "\n... (truncated, use --no-truncate for full content)")
                    else:
                        output.append(content)
            except json.JSONDecodeError:
                # If not JSON, show raw text
                if len(content) > 2000:
                    output.append(content[:2000] + "\n... (truncated)")
                else:
                    output.append(content)
        
        return '\n'.join(output)
    
    def execute_current_request(self, timeout: int = 30):
        """Execute the current request live"""
        if not self.entries:
            print("No requests found in HAR file")
            return
        
        if 0 <= self.current_index < len(self.entries):
            entry = self.entries[self.current_index]
            result = self.execute_request_live(entry, timeout)
            print(self.format_live_response(result))
        else:
            print("Invalid request index")
    
    def execute_request_by_number(self, request_num: int, timeout: int = 30):
        """Execute specific request by number (1-based)"""
        if 1 <= request_num <= len(self.entries):
            entry = self.entries[request_num - 1]
            result = self.execute_request_live(entry, timeout)
            print(self.format_live_response(result))
        else:
            print(f"Invalid request number. Range: 1-{len(self.entries)}")
    
    def generate_python_code_for_entry(self, entry: Dict[str, Any], request_num: int) -> str:
        """Generate Python code for a single HAR entry"""
        request_details = self.extract_request_details(entry)
        
        method = request_details['method']
        url = request_details['url']
        headers = request_details['headers']
        body = request_details['body']
        
        # Start building the Python code
        lines = []
        lines.append(f"# Request {request_num}: {method} {url}")
        lines.append(f"def request_{request_num}():")
        lines.append(f'    """Execute request {request_num}: {method} {urlparse(url).netloc}"""')
        lines.append(f"    print(f'Executing request {request_num}: {method} {{url[:50]}}...')")
        lines.append("")
        
        # URL
        lines.append(f'    url = "{url}"')
        lines.append("")
        
        # Headers
        if headers:
            lines.append("    headers = {")
            for name, value in headers.items():
                # Escape quotes in header values
                escaped_value = value.replace('"', '\\"').replace("'", "\\'")
                lines.append(f'        "{name}": "{escaped_value}",')
            lines.append("    }")
        else:
            lines.append("    headers = {}")
        lines.append("")
        
        # Body/Data
        if body:
            lines.append("    data = '''")
            # Handle multi-line data
            for line in body.split('\n'):
                lines.append(f"{line}")
            lines.append("'''")
        else:
            lines.append("    data = None")
        lines.append("")
        
        # Make the request
        lines.append("    try:")
        lines.append("        response = requests.request(")
        lines.append(f'            method="{method}",')
        lines.append("            url=url,")
        lines.append("            headers=headers,")
        lines.append("            data=data,")
        lines.append("            timeout=30,")
        lines.append("            allow_redirects=True,")
        lines.append("            verify=True")
        lines.append("        )")
        lines.append("")
        lines.append("        print(f'✅ Response: {response.status_code} {response.reason}')")
        lines.append("        print(f'Response Time: {response.elapsed.total_seconds():.3f}s')")
        lines.append("        print(f'Content Length: {len(response.content)} bytes')")
        lines.append("")
        lines.append("        # Pretty print JSON responses")
        lines.append("        if response.headers.get('content-type', '').startswith('application/json'):")
        lines.append("            try:")
        lines.append("                json_data = response.json()")
        lines.append("                print('Response JSON:')")
        lines.append("                print(json.dumps(json_data, indent=2))")
        lines.append("            except json.JSONDecodeError:")
        lines.append("                print('Response Text:')")
        lines.append("                print(response.text[:1000] + ('...' if len(response.text) > 1000 else ''))")
        lines.append("        else:")
        lines.append("            print('Response Text:')")
        lines.append("            print(response.text[:1000] + ('...' if len(response.text) > 1000 else ''))")
        lines.append("")
        lines.append("        return response")
        lines.append("")
        lines.append("    except requests.exceptions.Timeout:")
        lines.append("        print('❌ Request timed out')")
        lines.append("        return None")
        lines.append("    except requests.exceptions.ConnectionError as e:")
        lines.append("        print(f'❌ Connection error: {e}')")
        lines.append("        return None")
        lines.append("    except requests.exceptions.RequestException as e:")
        lines.append("        print(f'❌ Request failed: {e}')")
        lines.append("        return None")
        lines.append("    except Exception as e:")
        lines.append("        print(f'❌ Unexpected error: {e}')")
        lines.append("        return None")
        lines.append("")
        
        return '\n'.join(lines)
    
    def generate_python_script(self, output_filename: str, include_all: bool = True, request_numbers: List[int] = None):
        """Generate a complete Python script from HAR entries"""
        if not self.entries:
            print("No entries found in HAR file")
            return
        
        if request_numbers:
            # Validate request numbers
            invalid_nums = [n for n in request_numbers if n < 1 or n > len(self.entries)]
            if invalid_nums:
                print(f"Invalid request numbers: {invalid_nums}. Range: 1-{len(self.entries)}")
                return
            entries_to_process = [(n, self.entries[n-1]) for n in request_numbers]
        elif include_all:
            entries_to_process = [(i+1, entry) for i, entry in enumerate(self.entries)]
        else:
            print("No requests specified")
            return
        
        print(f"Generating Python script with {len(entries_to_process)} requests...")
        
        # Build the complete Python script
        script_lines = []
        
        # File header
        script_lines.append('#!/usr/bin/env python3')
        script_lines.append('"""')
        script_lines.append(f'Generated Python script from HAR file: {self.har_file_path}')
        script_lines.append(f'Total requests: {len(entries_to_process)}')
        script_lines.append(f'Generated on: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
        script_lines.append('"""')
        script_lines.append('')
        
        # Imports
        script_lines.append('import requests')
        script_lines.append('import json')
        script_lines.append('import time')
        script_lines.append('from datetime import datetime')
        script_lines.append('')
        
        # Add each request function
        for request_num, entry in entries_to_process:
            python_code = self.generate_python_code_for_entry(entry, request_num)
            script_lines.append(python_code)
        
        # Main execution section
        script_lines.append('def main():')
        script_lines.append('    """Execute all requests in sequence"""')
        script_lines.append('    print("Starting HAR replay script...")')
        script_lines.append(f'    print("Total requests to execute: {len(entries_to_process)}")')
        script_lines.append('    print("=" * 80)')
        script_lines.append('')
        
        script_lines.append('    results = {}')
        script_lines.append('    start_time = time.time()')
        script_lines.append('')
        
        for request_num, _ in entries_to_process:
            script_lines.append(f'    # Execute request {request_num}')
            script_lines.append(f'    print("\\n" + "-" * 40)')
            script_lines.append(f'    response = request_{request_num}()')
            script_lines.append(f'    results[{request_num}] = response')
            script_lines.append(f'    time.sleep(0.5)  # Brief pause between requests')
            script_lines.append('')
        
        script_lines.append('    # Summary')
        script_lines.append('    end_time = time.time()')
        script_lines.append('    total_time = end_time - start_time')
        script_lines.append('')
        script_lines.append('    print("=" * 80)')
        script_lines.append('    print("EXECUTION SUMMARY")')
        script_lines.append('    print("=" * 80)')
        script_lines.append('    print(f"Total execution time: {total_time:.2f} seconds")')
        script_lines.append('')
        script_lines.append('    successful = 0')
        script_lines.append('    failed = 0')
        script_lines.append('')
        script_lines.append('    for req_num, response in results.items():')
        script_lines.append('        if response and response.status_code < 400:')
        script_lines.append('            print(f"✅ Request {req_num}: {response.status_code}")')
        script_lines.append('            successful += 1')
        script_lines.append('        else:')
        script_lines.append('            status = response.status_code if response else "Failed"')
        script_lines.append('            print(f"❌ Request {req_num}: {status}")')
        script_lines.append('            failed += 1')
        script_lines.append('')
        script_lines.append('    print(f"\\nSuccessful: {successful}, Failed: {failed}")')
        script_lines.append('')
        
        # Individual execution functions
        script_lines.append('')
        script_lines.append('def execute_single(request_num: int):')
        script_lines.append('    """Execute a single request by number"""')
        script_lines.append('    function_map = {')
        for request_num, _ in entries_to_process:
            script_lines.append(f'        {request_num}: request_{request_num},')
        script_lines.append('    }')
        script_lines.append('')
        script_lines.append('    if request_num in function_map:')
        script_lines.append('        print(f"Executing request {request_num}...")')
        script_lines.append('        return function_map[request_num]()')
        script_lines.append('    else:')
        script_lines.append(f'        print(f"Invalid request number. Available: {[n for n, _ in entries_to_process]}")')
        script_lines.append('        return None')
        script_lines.append('')
        
        # Command line interface
        script_lines.append('')
        script_lines.append('if __name__ == "__main__":')
        script_lines.append('    import sys')
        script_lines.append('')
        script_lines.append('    if len(sys.argv) > 1:')
        script_lines.append('        # Execute specific request number')
        script_lines.append('        try:')
        script_lines.append('            request_num = int(sys.argv[1])')
        script_lines.append('            execute_single(request_num)')
        script_lines.append('        except ValueError:')
        script_lines.append('            print("Usage: python script.py [request_number]")')
        script_lines.append('            print(f"Available request numbers: {[n for n, _ in entries_to_process]}")')
        script_lines.append('    else:')
        script_lines.append('        # Execute all requests')
        script_lines.append('        main()')
        
        # Write the script to file
        try:
            with open(output_filename, 'w', encoding='utf-8') as f:
                f.write('\n'.join(script_lines))
            
            print(f"✅ Python script generated: {output_filename}")
            print(f"📊 Included {len(entries_to_process)} requests")
            print()
            print("Usage:")
            print(f"  python {output_filename}                    # Execute all requests")
            print(f"  python {output_filename} <request_num>      # Execute specific request")
            print()
            print("Example:")
            print(f"  python {output_filename} {entries_to_process[0][0]}                    # Execute first request")
            
        except Exception as e:
            print(f"❌ Error writing Python script: {e}")
    
    def generate_python_for_current(self, output_filename: str):
        """Generate Python code for current request only"""
        if not self.entries:
            print("No requests found in HAR file")
            return
        
        if 0 <= self.current_index < len(self.entries):
            self.generate_python_script(output_filename, include_all=False, request_numbers=[self.current_index + 1])
        else:
            print("Invalid current request index")
    
    def generate_python_for_numbers(self, output_filename: str, request_numbers: List[int]):
        """Generate Python code for specific request numbers"""
        self.generate_python_script(output_filename, include_all=False, request_numbers=request_numbers)
    
    def show_current_request(self):
        """Display the current request"""
        if not self.entries:
            print("No requests found in HAR file")
            return
        
        if 0 <= self.current_index < len(self.entries):
            entry = self.entries[self.current_index]
            print(self.format_request_info(entry))
        else:
            print("Invalid request index")
    
    def show_current_response(self):
        """Display the current request's response details"""
        if not self.entries:
            print("No requests found in HAR file")
            return
        
        if 0 <= self.current_index < len(self.entries):
            entry = self.entries[self.current_index]
            print(self.format_response_details(entry))
        else:
            print("Invalid request index")
    
    def show_current_complete(self):
        """Display the complete current request and response"""
        if not self.entries:
            print("No requests found in HAR file")
            return
        
        if 0 <= self.current_index < len(self.entries):
            entry = self.entries[self.current_index]
            print(self.show_complete_request(entry))
        else:
            print("Invalid request index")
    
    def show_complete_request_by_number(self, request_num: int):
        """Show complete request and response by number (1-based)"""
        if 1 <= request_num <= len(self.entries):
            entry = self.entries[request_num - 1]
            print(self.show_complete_request(entry))
        else:
            print(f"Invalid request number. Range: 1-{len(self.entries)}")
            
    def show_response_by_number(self, request_num: int):
        """Show only response details by number (1-based)"""
        if 1 <= request_num <= len(self.entries):
            entry = self.entries[request_num - 1]
            print(self.format_response_details(entry))
        else:
            print(f"Invalid request number. Range: 1-{len(self.entries)}")
    
    def show_giftcard_summary(self):
        """Show a summary of gift card related requests"""
        giftcard_requests = []
        
        for i, entry in enumerate(self.entries):
            request = entry.get('request', {})
            url = request.get('url', '').lower()
            
            if any(keyword in url for keyword in ['giftcard', 'gift_card', 'gift-card']):
                method = request.get('method', 'UNKNOWN')
                status = entry.get('response', {}).get('status', 'NO_RESPONSE')
                giftcard_requests.append((i, method, url, status))
        
        print("=" * 80)
        print("GIFT CARD RELATED REQUESTS SUMMARY")
        print("=" * 80)
        
        if not giftcard_requests:
            print("No gift card related requests found")
        else:
            for i, (index, method, url, status) in enumerate(giftcard_requests):
                domain_match = re.search(r'https?://([^/]+)', url)
                domain = domain_match.group(1) if domain_match else 'unknown'
                path = url.split(domain, 1)[1] if domain in url else url
                if len(path) > 60:
                    path = path[:60] + "..."
                print(f"{i+1:2d}. [{index+1:3d}] {method:4s} {status:3d} {domain} {path}")

    def show_all_requests_summary(self):
        """Show a summary of all requests with URLs, methods, and response sizes"""
        print("=" * 100)
        print("ALL REQUESTS SUMMARY")
        print("=" * 100)
        print(f"{'#':<4} {'Method':<6} {'Status':<6} {'Size':<8} {'URL'}")
        print("-" * 100)
        
        for i, entry in enumerate(self.entries):
            request = entry.get('request', {})
            response = entry.get('response', {})
            
            method = request.get('method', 'UNKNOWN')
            url = request.get('url', 'UNKNOWN')
            status = response.get('status', 'N/A')
            
            # Get response size
            content = response.get('content', {})
            size = content.get('size', 0)
            if size == 0:
                size_str = "N/A"
            elif size < 1024:
                size_str = f"{size}B"
            elif size < 1024 * 1024:
                size_str = f"{size/1024:.1f}KB"
            else:
                size_str = f"{size/(1024*1024):.1f}MB"
            
            # Truncate URL if too long
            display_url = url
            max_url_length = 75
            if len(url) > max_url_length:
                display_url = url[:max_url_length] + "..."
            
            print(f"{i+1:<4} {method:<6} {status:<6} {size_str:<8} {display_url}")
    
    def navigate(self, timeout: int = 30):
        """Interactive navigation through requests"""
        print("HAR Preview Tool - Gift Card Flow Analysis")
        print("Commands: n(ext), p(rev), g(oto) <num>, r(esponse), c(omplete), e(xecute), py(thon), s(ummary), a(ll-summary), q(uit), h(elp)")
        print()
        
        self.show_giftcard_summary()
        print()
        
        while True:
            print()
            print(f"Current position: {self.current_index + 1}/{len(self.entries)}")
            command = input("Enter command (h for help): ").strip().lower()
            
            if command == 'q' or command == 'quit':
                break
            elif command == 'n' or command == 'next':
                if self.current_index < len(self.entries) - 1:
                    self.current_index += 1
                    self.show_current_request()
                else:
                    print("Already at the last request")
            elif command == 'p' or command == 'prev':
                if self.current_index > 0:
                    self.current_index -= 1
                    self.show_current_request()
                else:
                    print("Already at the first request")
            elif command.startswith('g') or command.startswith('goto'):
                try:
                    parts = command.split()
                    if len(parts) > 1:
                        index = int(parts[1]) - 1  # Convert to 0-based
                        if 0 <= index < len(self.entries):
                            self.current_index = index
                            self.show_current_request()
                        else:
                            print(f"Invalid index. Range: 1-{len(self.entries)}")
                    else:
                        index_str = input("Enter request number: ").strip()
                        index = int(index_str) - 1
                        if 0 <= index < len(self.entries):
                            self.current_index = index
                            self.show_current_request()
                        else:
                            print(f"Invalid index. Range: 1-{len(self.entries)}")
                except ValueError:
                    print("Invalid number")
            elif command == 'r' or command == 'response':
                self.show_current_response()
            elif command == 'c' or command == 'complete':
                self.show_current_complete()
            elif command == 'e' or command == 'execute':
                print("\u26a0\ufe0f  WARNING: This will make a live HTTP request!")
                confirm = input("Are you sure you want to execute this request? (y/N): ").strip().lower()
                if confirm in ['y', 'yes']:
                    self.execute_current_request(timeout)
                else:
                    print("Request execution cancelled")
            elif command.startswith('ex ') or command.startswith('execute '):
                try:
                    parts = command.split()
                    if len(parts) > 1:
                        request_num = int(parts[1])
                        print(f"\u26a0\ufe0f  WARNING: This will make a live HTTP request for request #{request_num}!")
                        confirm = input("Are you sure you want to execute this request? (y/N): ").strip().lower()
                        if confirm in ['y', 'yes']:
                            self.execute_request_by_number(request_num, timeout)
                        else:
                            print("Request execution cancelled")
                    else:
                        request_num_str = input("Enter request number to execute: ").strip()
                        request_num = int(request_num_str)
                        print(f"\u26a0\ufe0f  WARNING: This will make a live HTTP request for request #{request_num}!")
                        confirm = input("Are you sure you want to execute this request? (y/N): ").strip().lower()
                        if confirm in ['y', 'yes']:
                            self.execute_request_by_number(request_num, timeout)
                        else:
                            print("Request execution cancelled")
                except ValueError:
                    print("Invalid number")
            elif command.startswith('py') or command.startswith('python'):
                try:
                    parts = command.split()
                    if len(parts) > 1:
                        # Specific format: py <filename> [request_nums...]
                        output_filename = parts[1]
                        if len(parts) > 2:
                            # Specific request numbers
                            request_nums = [int(x) for x in parts[2:]]
                            self.generate_python_for_numbers(output_filename, request_nums)
                        else:
                            # Current request only
                            self.generate_python_for_current(output_filename)
                    else:
                        # Ask for filename
                        filename = input("Enter output filename (e.g., script.py): ").strip()
                        if not filename:
                            print("Filename required")
                            continue
                        if not filename.endswith('.py'):
                            filename += '.py'
                        
                        choice = input("Generate for: (c)urrent request, (a)ll requests, or (s)pecific numbers? ").strip().lower()
                        if choice == 'c' or choice == 'current':
                            self.generate_python_for_current(filename)
                        elif choice == 'a' or choice == 'all':
                            self.generate_python_script(filename, include_all=True)
                        elif choice == 's' or choice == 'specific':
                            numbers_str = input("Enter request numbers (comma-separated, e.g., 1,3,5): ").strip()
                            try:
                                request_nums = [int(x.strip()) for x in numbers_str.split(',') if x.strip()]
                                self.generate_python_for_numbers(filename, request_nums)
                            except ValueError:
                                print("Invalid request numbers")
                        else:
                            print("Invalid choice")
                except ValueError:
                    print("Invalid number in request numbers")
                except Exception as e:
                    print(f"Error generating Python: {e}")
            elif command.startswith('rc') or command.startswith('response-complete'):
                try:
                    parts = command.split()
                    if len(parts) > 1:
                        request_num = int(parts[1])
                        self.show_complete_request_by_number(request_num)
                    else:
                        request_num_str = input("Enter request number for complete view: ").strip()
                        request_num = int(request_num_str)
                        self.show_complete_request_by_number(request_num)
                except ValueError:
                    print("Invalid number")
            elif command.startswith('rr') or command.startswith('response-only'):
                try:
                    parts = command.split()
                    if len(parts) > 1:
                        request_num = int(parts[1])
                        self.show_response_by_number(request_num)
                    else:
                        request_num_str = input("Enter request number for response: ").strip()
                        request_num = int(request_num_str)
                        self.show_response_by_number(request_num)
                except ValueError:
                    print("Invalid number")
            elif command == 's' or command == 'summary':
                self.show_giftcard_summary()
            elif command == 'a' or command == 'all' or command == 'all-summary':
                self.show_all_requests_summary()
            elif command == 'h' or command == 'help':
                print("Commands:")
                print("  n, next              - Show next request")
                print("  p, prev              - Show previous request")
                print("  g <num>              - Go to request number")
                print("  r, response          - Show response details for current request")
                print("  c, complete          - Show complete request+response for current")
                print("  e, execute           - Execute current request LIVE (with confirmation)")
                print("  ex <num>             - Execute specific request number LIVE (with confirmation)")
                print("  py <filename>        - Generate Python script for current request")
                print("  py <filename> <nums> - Generate Python script for specific request numbers")
                print("  python               - Generate Python script (interactive prompts)")
                print("  rc <num>             - Show complete request+response for specific number")
                print("  rr <num>             - Show only response details for specific number")
                print("  s, summary           - Show gift card requests summary")
                print("  a, all-summary       - Show all requests summary")
                print("  q, quit              - Exit the tool")
                print("  h, help              - Show this help")
                print("")
                print("\u26a0\ufe0f  WARNING: 'execute' commands make real HTTP requests!")
                print("💡 TIP: 'python' commands generate executable Python scripts from HAR data")
            elif command == '':
                self.show_current_request()
            else:
                print("Unknown command. Type 'h' for help.")

    def show_request_by_number(self, request_num: int):
        """Show a specific request by number (1-based)"""
        if 1 <= request_num <= len(self.entries):
            self.current_index = request_num - 1
            self.show_current_request()
        else:
            print(f"Invalid request number. Range: 1-{len(self.entries)}")
            sys.exit(1)

def main():
    parser = argparse.ArgumentParser(
        description="HAR Preview Tool - Navigate through HAR file requests one at a time",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python har_preview.py order_giftcard.har                       # Interactive mode
  python har_preview.py order_giftcard.har --request 1           # Show request #1 and exit
  python har_preview.py order_giftcard.har --complete 5          # Show complete request+response #5 and exit
  python har_preview.py order_giftcard.har --response 3          # Show only response details #3 and exit
  python har_preview.py order_giftcard.har --execute 5           # Execute request #5 LIVE and exit (with confirmation)
  python har_preview.py order_giftcard.har --execute 5 --no-confirm  # Execute request #5 LIVE without confirmation
  python har_preview.py order_giftcard.har --execute 5 --timeout 60  # Execute with 60 second timeout
  python har_preview.py order_giftcard.har --generate-python script.py  # Generate Python script for all requests
  python har_preview.py order_giftcard.har --generate-python script.py --python-requests "1,3,5"  # Generate for specific requests
  python har_preview.py order_giftcard.har --summary             # Show gift card summary only
  python har_preview.py order_giftcard.har --all-summary         # Show all requests summary
  python har_preview.py order_giftcard.har --execute 5 --interactive # Execute #5 then enter interactive mode

Interactive Mode Commands:
  e, execute           - Execute current request LIVE (with confirmation)  
  ex <num>             - Execute specific request number LIVE (with confirmation)
  py <filename>        - Generate Python script for current request
  py <filename> <nums> - Generate Python script for specific request numbers
  python               - Generate Python script (interactive prompts)
  
Generated Python Scripts:
  python script.py                    # Execute all requests in sequence
  python script.py <request_number>   # Execute specific request only
  
WARNING: --execute commands make real HTTP requests to live servers!
        """
    )
    
    parser.add_argument('har_file', help='Path to the HAR file to analyze')
    parser.add_argument(
        '-r', '--request', 
        type=int, 
        help='Show specific request number (1-based) and exit'
    )
    parser.add_argument(
        '--complete', 
        type=int, 
        help='Show complete request and response details for specific request number (1-based) and exit'
    )
    parser.add_argument(
        '--response', 
        type=int, 
        help='Show only response details for specific request number (1-based) and exit'
    )
    parser.add_argument(
        '--execute', 
        type=int, 
        help='Execute specific request number (1-based) LIVE and exit - WARNING: Makes real HTTP requests!'
    )
    parser.add_argument(
        '--timeout', 
        type=int, 
        default=30,
        help='Timeout for live requests in seconds (default: 30)'
    )
    parser.add_argument(
        '--no-confirm', 
        action='store_true', 
        help='Skip confirmation prompts for live execution (DANGEROUS)'
    )
    parser.add_argument(
        '--generate-python', 
        type=str, 
        help='Generate Python script from HAR and save to specified filename'
    )
    parser.add_argument(
        '--python-requests', 
        type=str, 
        help='Comma-separated request numbers to include in Python script (e.g., "1,3,5")'
    )
    parser.add_argument(
        '-s', '--summary', 
        action='store_true', 
        help='Show gift card requests summary only and exit'
    )
    parser.add_argument(
        '--all-summary', 
        action='store_true', 
        help='Show summary of all requests with URLs, methods, and response sizes'
    )
    parser.add_argument(
        '--interactive', 
        action='store_true', 
        help='Force interactive mode even when other flags are used'
    )
    
    args = parser.parse_args()
    
    # Create preview instance
    preview = HARPreview(args.har_file)
    
    # Handle Python generation
    if args.generate_python:
        if args.python_requests:
            # Generate Python for specific request numbers
            try:
                request_nums = [int(x.strip()) for x in args.python_requests.split(',') if x.strip()]
                if args.interactive:
                    preview.generate_python_for_numbers(args.generate_python, request_nums)
                    print("\n" + "="*80)
                    print("Entering interactive mode...")
                    print("="*80)
                    preview.navigate(args.timeout)
                else:
                    preview.generate_python_for_numbers(args.generate_python, request_nums)
            except ValueError:
                print("Invalid request numbers in --python-requests")
                sys.exit(1)
        else:
            # Generate Python for all requests
            if args.interactive:
                preview.generate_python_script(args.generate_python, include_all=True)
                print("\n" + "="*80)
                print("Entering interactive mode...")
                print("="*80)
                preview.navigate(args.timeout)
            else:
                preview.generate_python_script(args.generate_python, include_all=True)
                
    # Handle different modes
    elif args.execute:
        if not args.no_confirm:
            print(f"\u26a0\ufe0f  WARNING: This will execute request #{args.execute} LIVE!")
            print("This will make a real HTTP request to the target server.")
            confirm = input("Are you sure you want to continue? (y/N): ").strip().lower()
            if confirm not in ['y', 'yes']:
                print("Request execution cancelled")
                sys.exit(0)
        
        if args.interactive:
            # Execute then enter interactive mode
            preview.execute_request_by_number(args.execute, args.timeout)
            print("\n" + "="*80)
            print("Entering interactive mode...")
            print("="*80)
            preview.navigate(args.timeout)
        else:
            # Just execute and exit
            preview.execute_request_by_number(args.execute, args.timeout)
    elif args.complete:
        if args.interactive:
            # Show complete request then enter interactive mode
            preview.show_complete_request_by_number(args.complete)
            print("\n" + "="*80)
            print("Entering interactive mode...")
            print("="*80)
            preview.navigate(args.timeout)
        else:
            # Just show the complete request and exit
            preview.show_complete_request_by_number(args.complete)
    elif args.response:
        if args.interactive:
            # Show response then enter interactive mode
            preview.show_response_by_number(args.response)
            print("\n" + "="*80)
            print("Entering interactive mode...")
            print("="*80)
            preview.navigate(args.timeout)
        else:
            # Just show the response and exit
            preview.show_response_by_number(args.response)
    elif args.request:
        if args.interactive:
            # Show specific request then enter interactive mode
            preview.show_request_by_number(args.request)
            print("\n" + "="*80)
            print("Entering interactive mode...")
            print("="*80)
            preview.navigate(args.timeout)
        else:
            # Just show the specific request and exit
            preview.show_request_by_number(args.request)
    elif args.all_summary:
        if args.interactive:
            # Show all requests summary then enter interactive mode
            preview.show_all_requests_summary()
            print("\n" + "="*80)
            print("Entering interactive mode...")
            print("="*80)
            preview.navigate(args.timeout)
        else:
            # Just show the all requests summary and exit
            preview.show_all_requests_summary()
    elif args.summary:
        if args.interactive:
            # Show summary then enter interactive mode
            preview.show_giftcard_summary()
            print("\n" + "="*80)
            print("Entering interactive mode...")
            print("="*80)
            preview.navigate(args.timeout)
        else:
            # Just show the summary and exit
            preview.show_giftcard_summary()
    else:
        # Default interactive mode
        preview.navigate(args.timeout)

if __name__ == "__main__":
    main() 